#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#

import logging
from itertools import zip_longest
from pathlib import Path

import saneyaml
from django.db import transaction

from aboutcode.hashid import get_core_purl
from aboutcode.pipeline import LoopProgress
from fedcode.models import Package
from fedcode.models import Repository
from fedcode.models import Vulnerability
from fedcode.pipelines import FederatedCodePipeline
from fedcode.pipes import utils


class SyncVulnerableCode(FederatedCodePipeline):
    """Sync VulnerableCode data from FederatedCode git repositories."""

    pipeline_id = "sync_vulnerablecode"

    @classmethod
    def steps(cls):
        return (
            cls.get_git_repos,
            cls.sync_vulnerablecode_repositories,
        )

    def get_git_repos(self):
        self.git_repos = Repository.objects.all()

    def sync_vulnerablecode_repositories(self):
        """
        Sync repositories
        For vulnerablecode-data we have 3 files types vulnerabilities.yml, purls.yml, VCID-1ues-ahar-buaa.yml
        """
        repositories_count = self.git_repos.count()
        self.log(f"Syncing vulnerability from {repositories_count:,d} repositories")

        progress = LoopProgress(total_iterations=repositories_count, logger=self.log)
        for repository in progress.iter(self.git_repos.iterator(chunk_size=2000)):
            repository.git_repo_obj.remotes.origin.pull()
            sync_vulnerabilities(
                repository=repository,
                logger=self.log,
            )


def sync_vulnerabilities(repository, logger):
    repo = repository.git_repo_obj
    latest_commit_hash = repo.head.commit.hexsha
    latest_commit = repo.commit(latest_commit_hash)

    if repository.last_imported_commit:
        last_imported_commit = repo.commit(repository.last_imported_commit)
        diffs = last_imported_commit.diff(latest_commit)
    else:
        last_imported_commit = None
        # Diff between empty trees and last_imported_commit
        diffs = latest_commit.diff("4b825dc642cb6eb9a060e54bf8d69288fbee4904", R=True)

    if repo.head.commit.hexsha == repository.last_imported_commit:
        logger("Nothing to import!", level=logging.ERROR)
        return

    diff_count = len(diffs)

    logger(f"Syncing {diff_count:,d} vulnerability scan from {repository.url}")
    progress = LoopProgress(total_iterations=diff_count, logger=logger)
    for diff in progress.iter(diffs):
        if not diff.a_path.endswith(".yml"):
            continue

        if diff.a_path.startswith("."):
            continue

        yaml_data_a_blob = saneyaml.load(diff.a_blob.data_stream.read()) if diff.a_blob else None
        yaml_data_b_blob = saneyaml.load(diff.b_blob.data_stream.read()) if diff.b_blob else None

        a_name = Path(diff.a_path).name
        b_name = Path(diff.b_path).name

        if a_name == "vulnerabilities.yml" or b_name == "vulnerabilities.yml":
            note_handler(
                diff.change_type, repository.admin, yaml_data_a_blob, yaml_data_b_blob, logger
            )

        elif a_name == "purls.yml" or b_name == "purls.yml":
            pkg_handler(
                diff.change_type,
                repository.admin,
                yaml_data_a_blob,
                yaml_data_b_blob,
                logger,
            )

        elif a_name.startswith("VCID") or b_name.startswith("VCID"):
            vul_handler(diff.change_type, repository, yaml_data_a_blob, yaml_data_b_blob, logger)

    repository.last_imported_commit = latest_commit_hash
    repository.save()
    logger("The Importer run successfully")


def vul_handler(change_type, repo_obj, yaml_data_a_blob, yaml_data_b_blob, logger):
    """
    Handle changes in VCID-XXXX-XXXX-XXXX.yml
    """
    vulnerability_a_id = yaml_data_a_blob.get("vulnerability_id") if yaml_data_a_blob else None
    vulnerability_b_id = yaml_data_b_blob.get("vulnerability_id") if yaml_data_b_blob else None

    if change_type == "A":  # Added
        Vulnerability.objects.get_or_create(
            id=vulnerability_b_id,
            repo=repo_obj,
        )

    elif change_type in ["M", "R"]:  # Modified or Renamed
        with transaction.atomic():
            if vulnerability_a_id and vulnerability_a_id != vulnerability_b_id:
                # renamed or id changed
                Vulnerability.objects.filter(id=vulnerability_a_id, repo=repo_obj).delete()

            # update_or_create to avoid losing relations unnecessarily
            Vulnerability.objects.update_or_create(
                id=vulnerability_b_id,
                repo=repo_obj,
                defaults={},  # add fields parsed from yaml_data_b_blob here
            )

    elif change_type == "D":  # Deleted
        if vulnerability_a_id:
            Vulnerability.objects.filter(id=vulnerability_a_id, repo=repo_obj).delete()

    else:
        logger(f"Invalid Vulnerability File", level=logging.ERROR)


def pkg_handler(change_type, default_service, yaml_data_a_blob, yaml_data_b_blob, logger):
    """
    Handle changes in purls.yml
    """

    if change_type == "A":  # Added packages
        for purl in yaml_data_b_blob or []:
            core_purl = get_core_purl(purl)
            Package.objects.get_or_create(purl=core_purl, service=default_service)

    elif change_type == "M":  # Modified packages
        for package_a, package_b in zip_longest(yaml_data_a_blob or [], yaml_data_b_blob or []):
            if not package_a or not package_b:
                continue  # skip if one side missing

            core_purl_a = get_core_purl(package_a)
            core_purl_b = get_core_purl(package_b)

            try:
                pkg = Package.objects.get(purl=core_purl_a, service=default_service)
            except Package.DoesNotExist:
                logger(f"Package not found for {core_purl_a}", level=logging.ERROR)
                continue

            # Update package purl if changed
            if pkg.purl != core_purl_b:
                pkg.purl = core_purl_b
                pkg.save()

    elif change_type == "D":  # Deleted packages
        for purl in yaml_data_a_blob or []:
            if not purl:
                logger("Invalid PURL in deleted entry", level=logging.ERROR)
                continue
            core_purl = get_core_purl(purl)
            try:
                pkg = Package.objects.get(purl=core_purl, service=default_service)
                pkg.delete()
            except Package.DoesNotExist:
                logger(f"Package not found for deletion: {core_purl}", level=logging.WARNING)

    else:
        logger(f"Unknown change_type: {change_type}", level=logging.ERROR)


def note_handler(change_type, default_service, yaml_data_a_blob, yaml_data_b_blob, logger):
    """
    Handle notes from vulnerabilities.yml changes.
    Uses zip_longest so both old (A) and new (B) entries are processed together.
    """

    for pkg_status_a, pkg_status_b in zip_longest(yaml_data_a_blob or [], yaml_data_b_blob or []):
        pkg_a = pkg_b = None

        # Resolve old package
        if pkg_status_a:
            purl_a = pkg_status_a.get("purl")
            if not purl_a:
                logger("Invalid Vulnerability File: missing purl in old entry", level=logging.ERROR)
            else:
                core_purl_a = get_core_purl(purl_a)
                pkg_a, _ = Package.objects.get_or_create(purl=core_purl_a, service=default_service)

        # Resolve new package
        if pkg_status_b:
            purl_b = pkg_status_b.get("purl")
            if not purl_b:
                logger("Invalid Vulnerability File: missing purl in new entry", level=logging.ERROR)
            else:
                core_purl_b = get_core_purl(purl_b)
                pkg_b, _ = Package.objects.get_or_create(purl=core_purl_b, service=default_service)

        if change_type == "A":  # Added entries
            if pkg_status_b and pkg_b:
                utils.create_note(pkg_b, saneyaml.dump(pkg_status_b))

        elif change_type == "M":  # Modified entries
            # Deleted entry
            if pkg_status_a and not pkg_status_b and pkg_a:
                utils.delete_note(pkg_a, saneyaml.dump(pkg_status_a))

            # Added entry
            elif pkg_status_b and not pkg_status_a and pkg_b:
                utils.create_note(pkg_b, saneyaml.dump(pkg_status_b))

            # Updated entry
            elif pkg_status_a and pkg_status_b and pkg_b:
                utils.update_note(pkg_b, saneyaml.dump(pkg_status_a), saneyaml.dump(pkg_status_b))

        elif change_type == "D":  # Deleted entries
            if pkg_status_a and pkg_a:
                utils.delete_note(pkg_a, saneyaml.dump(pkg_status_a))

        else:
            logger(f"Unknown change_type: {change_type}", level=logging.ERROR)
