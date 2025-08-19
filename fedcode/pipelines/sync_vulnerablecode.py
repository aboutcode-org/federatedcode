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
from fedcode.activitypub import Activity
from fedcode.activitypub import UpdateActivity
from fedcode.models import Note
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

        if a_name == "purls.yml" or b_name == "purls.yml":
            pkg_handler(
                diff.change_type, repository.admin, yaml_data_a_blob, yaml_data_b_blob, logger
            )

        if a_name.startswith("VCID") or b_name.startswith("VCID"):
            vul_handler(diff.change_type, repository, yaml_data_a_blob, yaml_data_b_blob, logger)

    repository.last_imported_commit = latest_commit_hash
    repository.save()
    logger("The Importer run successfully")


def vul_handler(change_type, repo_obj, yaml_data_a_blob, yaml_data_b_blob, logger):
    """
    VCID-XXXX-XXXX-XXXX.yml
    """
    vulnerability_a_id = yaml_data_a_blob.get("vulnerability_id") if yaml_data_a_blob else None
    vulnerability_b_id = yaml_data_b_blob.get("vulnerability_id") if yaml_data_b_blob else None

    if change_type == "A":  # A for added paths
        Vulnerability.objects.get_or_create(
            id=vulnerability_b_id,
            repo=repo_obj,
        )
    elif change_type in [
        "M",
        "R",
    ]:  # R for renamed paths , M for paths with modified data
        with transaction.atomic():
            Vulnerability.objects.get(id=vulnerability_a_id, repo=repo_obj).delete()
            Vulnerability.objects.create(id=vulnerability_b_id, repo=repo_obj)

    elif change_type == "D":  # D for deleted paths
        Vulnerability.objects.get(
            id=yaml_data_b_blob.get("vulnerability_id"),
            repo=repo_obj,
        ).delete()
    else:
        logger(f"Invalid Vulnerability File", level=logging.ERROR)


def pkg_handler(change_type, default_service, yaml_data_a_blob, yaml_data_b_blob, logger):
    """
    purls.yml
    """

    if change_type == "A":
        for purl in yaml_data_b_blob:
            core_purl = get_core_purl(purl)
            pkg, _ = Package.objects.get_or_create(purl=core_purl, service=default_service)

    # elif change_type == "M":
    #     pkg = Package.objects.get(purl=package_a, service=default_service)
    #     pkg.purl = package_b
    #     pkg.save()
    #
    #     for version_a, version_b in zip_longest(
    #         yaml_data_a_blob, yaml_data_b_blob
    #     ):
    #         if version_b and not version_a:
    #             utils.create_note(pkg, version_b)
    #
    #         if version_a and not version_b:
    #             utils.delete_note(pkg, version_a)
    #
    #         if version_a and version_b:
    #             note = Note.objects.get(acct=pkg.acct, content=saneyaml.dump(version_a))
    #             if note.content == saneyaml.dump(version_b):
    #                 continue
    #
    #             note.content = saneyaml.dump(version_b)
    #             note.save()
    #
    #             update_activity = UpdateActivity(actor=pkg.to_ap, object=note.to_ap)
    #             Activity.federate(
    #                 targets=pkg.followers_inboxes,
    #                 body=update_activity.to_ap(),
    #                 key_id=pkg.key_id,
    #             )
    #
    # elif change_type == "D":
    #     pkg = Package.objects.get(purl=package_a, service=default_service)
    #     for version in yaml_data_a_blob:
    #         utils.delete_note(pkg, version)
    #     pkg.delete()


def note_handler(change_type, default_service, yaml_data_a_blob, yaml_data_b_blob, logger):
    """
    vulnerabilities.yml
    """
    if change_type == "A":
        for pkg_status in yaml_data_b_blob:
            purl = pkg_status.get("purl")
            if not purl:
                logger(f"Invalid Vulnerability File", level=logging.ERROR)
                return
            core_purl = get_core_purl(purl)
            pkg_b, _ = Package.objects.get_or_create(purl=core_purl, service=default_service)
            temp = saneyaml.dump(pkg_status)
            utils.create_note(pkg_b, temp)

    # elif change_type == "M":
    #     for pkg_status_a, pkg_status_b in zip_longest(
    #         yaml_data_a_blob, yaml_data_b_blob
    #     ):
    #         if pkg_status_a and not pkg_status_b:
    #             utils.create_note(pkg_a, pkg_status_b)
    #
    #         if pkg_status_a and not pkg_status_b:
    #             utils.delete_note(pkg_a, pkg_status_b)
    #
    #         if pkg_status_a and pkg_status_b:
    #             utils.update_note(pkg_a, saneyaml.dump(pkg_status_a), saneyaml.dump(pkg_status_b))
    #
    # elif change_type == "D":
    #     for pkg_status in yaml_data_a_blob:
    #         purl = pkg_status.get("purl")
    #         if not purl:
    #             logger(f"Invalid Vulnerability File", level=logging.ERROR)
    #             return
    #         core_purl = get_core_purl(purl)
    #         pkg_a, _ = Package.objects.get_or_create(purl=core_purl, service=default_service)
    #         temp = saneyaml.dump(pkg_status)
    #         utils.delete_note(pkg_a, temp)
    else:
        logger(f"Invalid Vulnerability File", level=logging.ERROR)
