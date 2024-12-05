#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#

import logging
import os.path
from itertools import zip_longest

import saneyaml
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
        if not diff.a_path.endswith(".yaml"):
            continue

        if diff.a_path.startswith("."):
            continue

        yaml_data_a_blob = saneyaml.load(diff.a_blob.data_stream.read()) if diff.a_blob else None
        yaml_data_b_blob = saneyaml.load(diff.b_blob.data_stream.read()) if diff.b_blob else None

        if os.path.split(diff.a_path)[1].startswith("VCID") or os.path.split(diff.b_path)[
            1
        ].startswith("VCID"):
            vul_handler(
                diff.change_type,
                repository,
                yaml_data_a_blob,
                yaml_data_b_blob,
                logger,
            )
            continue

        pkg_handler(
            diff.change_type,
            repository.admin,
            yaml_data_a_blob,
            yaml_data_b_blob,
        )

    repository.last_imported_commit = latest_commit_hash
    repository.save()
    logger("The Importer run successfully")


def vul_handler(change_type, repo_obj, yaml_data_a_blob, yaml_data_b_blob, logger):
    if change_type == "A":  # A for added paths
        Vulnerability.objects.get_or_create(
            id=yaml_data_b_blob.get("vulnerability_id"),
            repo=repo_obj,
        )
    elif change_type in [
        "M",
        "R",
    ]:  # R for renamed paths , M for paths with modified data
        vul = Vulnerability.objects.get(
            id=yaml_data_a_blob.get("vulnerability_id"),
            repo=repo_obj,
        )
        vul.filename = yaml_data_b_blob.get("vulnerability_id")
        vul.save()
    elif change_type == "D":  # D for deleted paths
        vul = Vulnerability.objects.filter(
            id=yaml_data_b_blob.get("vulnerability_id"),
            repo=repo_obj,
        )
        vul.delete()
    else:
        logger(f"Invalid Vulnerability File", level=logging.ERROR)


def pkg_handler(change_type, default_service, yaml_data_a_blob, yaml_data_b_blob):
    if change_type == "A":
        package = yaml_data_b_blob.get("package")

        pkg, _ = Package.objects.get_or_create(purl=package, service=default_service)

        for version in yaml_data_b_blob.get("versions", []):
            utils.create_note(pkg, version)

    elif change_type == "M":
        old_package = yaml_data_a_blob.get("package")
        new_package = yaml_data_b_blob.get("package")

        pkg = Package.objects.get(purl=old_package, service=default_service)
        pkg.purl = new_package
        pkg.save()

        for version_a, version_b in zip_longest(
            yaml_data_a_blob.get("versions", []), yaml_data_b_blob.get("versions", [])
        ):
            if version_b and not version_a:
                utils.create_note(pkg, version_b)

            if version_a and not version_b:
                utils.delete_note(pkg, version_a)

            if version_a and version_b:
                note = Note.objects.get(acct=pkg.acct, content=saneyaml.dump(version_a))
                if note.content == saneyaml.dump(version_b):
                    continue

                note.content = saneyaml.dump(version_b)
                note.save()

                update_activity = UpdateActivity(actor=pkg.to_ap, object=note.to_ap)
                Activity.federate(
                    targets=pkg.followers_inboxes,
                    body=update_activity.to_ap(),
                    key_id=pkg.key_id,
                )

    elif change_type == "D":
        package = yaml_data_a_blob.get("package")
        pkg = Package.objects.get(purl=package, service=default_service)
        for version in yaml_data_a_blob.get("versions", []):
            utils.delete_note(pkg, version)
        pkg.delete()
