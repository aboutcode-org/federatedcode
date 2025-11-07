#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#
import json
import logging
from itertools import zip_longest
from pathlib import Path

import saneyaml
from django.db.models import Case
from django.db.models import Q
from django.db.models import TextField
from django.db.models import Value
from django.db.models import When

from aboutcode.hashid import get_core_purl
from aboutcode.pipeline import LoopProgress
from fedcode.activitypub import Activity
from fedcode.activitypub import CreateActivity
from fedcode.activitypub import DeleteActivity
from fedcode.activitypub import UpdateActivity
from fedcode.models import Note
from fedcode.models import Package
from fedcode.models import Repository
from fedcode.models import Vulnerability
from fedcode.pipelines import FederatedCodePipeline


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
    vul_files_processed = 0
    purl_files_processed = 0
    pkg_changes = {
        "create": [],
        "update": [],
        "delete": set(),
    }

    vul_changes = {"create": [], "update": [], "delete": set()}

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
            purl_files_processed += 1
            pkg_handler(
                diff.change_type,
                repository.admin,
                yaml_data_a_blob,
                yaml_data_b_blob,
                logger,
                pkg_changes,
            )

            if purl_files_processed % 10000 == 0:
                logger(
                    f"Processed {purl_files_processed} purls.yml files, flushing bulk changes..."
                )
                flush_pkg_changes(pkg_changes, logger)
                pkg_changes = {"create": [], "update": [], "delete": set()}

        elif a_name.startswith("VCID") or b_name.startswith("VCID"):
            vul_files_processed += 1
            vul_handler(
                diff.change_type,
                repository,
                yaml_data_a_blob,
                yaml_data_b_blob,
                logger,
                vul_changes,
            )

            if vul_files_processed % 10000 == 0:
                logger(f"Processed {vul_files_processed} VCID files, flushing bulk changes...")
                flush_vul_changes(vul_changes, logger)
                vul_changes = {"create": [], "update": [], "delete": set()}

    flush_pkg_changes(pkg_changes, logger)
    flush_vul_changes(vul_changes, logger)

    repository.last_imported_commit = latest_commit_hash
    repository.save()
    logger("The Importer run successfully")


def vul_handler(change_type, repo_obj, yaml_data_a_blob, yaml_data_b_blob, logger, vul_changes):
    """
    Collect changes in VCID-XXXX-XXXX-XXXX.yml files for bulk processing.
    """
    vulnerability_a_id = yaml_data_a_blob.get("vulnerability_id") if yaml_data_a_blob else None
    vulnerability_b_id = yaml_data_b_blob.get("vulnerability_id") if yaml_data_b_blob else None

    if change_type == "A":  # Added
        if vulnerability_b_id:
            vul_changes["create"].append(Vulnerability(id=vulnerability_b_id, repo=repo_obj))

    elif change_type in ["M", "R"]:  # Modified or Renamed
        if vulnerability_a_id and vulnerability_a_id != vulnerability_b_id:
            vul_changes["delete"].add((vulnerability_a_id, repo_obj))
        if vulnerability_b_id:
            vul_changes["update"].append((vulnerability_b_id, repo_obj))

    elif change_type == "D":  # Deleted
        if vulnerability_a_id:
            vul_changes["delete"].add((vulnerability_a_id, repo_obj))

    else:
        logger(f"Invalid Vulnerability File", level=logging.ERROR)


def pkg_handler(
    change_type, default_service, yaml_data_a_blob, yaml_data_b_blob, logger, pkg_changes
):
    """
    Handle changes in purls.yml but do not write immediately.
    Collects changes in pkg_changes dict for bulk flush later.
    """

    if change_type == "A":
        for purl in yaml_data_b_blob or []:
            core_purl = get_core_purl(purl)
            pkg_changes["create"].append(Package(purl=core_purl, service=default_service))

    elif change_type == "M":
        for package_a, package_b in zip_longest(yaml_data_a_blob or [], yaml_data_b_blob or []):
            if not package_a or not package_b:
                continue
            core_purl_a = get_core_purl(package_a)
            core_purl_b = get_core_purl(package_b)
            pkg_changes["update"].append((core_purl_a, core_purl_b, default_service))

    elif change_type == "D":
        for purl in yaml_data_a_blob or []:
            if not purl:
                logger("Invalid PURL in deleted entry", level=logging.ERROR)
                continue
            core_purl = get_core_purl(purl)
            pkg_changes["delete"].add((core_purl, default_service))

    else:
        logger(f"Unknown change_type: {change_type}", level=logging.ERROR)


def flush_pkg_changes(pkg_changes, logger):
    if pkg_changes["create"]:
        Package.objects.bulk_create(pkg_changes["create"], ignore_conflicts=True)

    if pkg_changes["update"]:
        updates = []
        for old_purl, new_purl, service in pkg_changes["update"]:
            try:
                pkg = Package.objects.get(purl=old_purl, service=service)
                if pkg.purl != new_purl:
                    pkg.purl = new_purl
                    updates.append(pkg)
            except Package.DoesNotExist:
                logger(f"Package not found for {old_purl}", level=logging.WARNING)
        if updates:
            Package.objects.bulk_update(updates, ["purl"])

    if pkg_changes["delete"]:
        purls, services = zip(*pkg_changes["delete"])
        Package.objects.filter(purl__in=purls, service__in=services).delete()


def flush_vul_changes(vul_changes, logger):
    if vul_changes["create"]:
        Vulnerability.objects.bulk_create(vul_changes["create"], ignore_conflicts=True)

    if vul_changes["update"]:
        updates = []
        for vul_id, repo_obj in vul_changes["update"]:
            try:
                vul = Vulnerability.objects.get(id=vul_id, repo=repo_obj)
                updates.append(vul)
            except Vulnerability.DoesNotExist:
                updates.append(Vulnerability(id=vul_id, repo=repo_obj))
        if updates:
            Vulnerability.objects.bulk_update(updates, ["repo"])

    if vul_changes["delete"]:
        vul_ids, repos = zip(*vul_changes["delete"])
        Vulnerability.objects.filter(id__in=vul_ids, repo__in=repos).delete()


def note_handler(change_type, default_service, yaml_data_a_blob, yaml_data_b_blob, logger):
    """
    Handle notes from vulnerabilities.yml changes.
    Uses zip_longest so both old (A) and new (B) entries are processed together.
    """
    notes_to_create = []
    notes_to_update = []
    notes_to_delete = []

    purls_to_fetch = set()
    for pkg_status_a, pkg_status_b in zip_longest(yaml_data_a_blob or [], yaml_data_b_blob or []):
        if pkg_status_a:
            purl_a = pkg_status_a.get("purl")
            if purl_a:
                purls_to_fetch.add(get_core_purl(purl_a))
            else:
                logger("Invalid Vulnerability File: missing purl in old entry", level=logging.ERROR)

        if pkg_status_b:
            purl_b = pkg_status_b.get("purl")
            if purl_b:
                purls_to_fetch.add(get_core_purl(purl_b))
            else:
                logger("Invalid Vulnerability File: missing purl in new entry", level=logging.ERROR)

    packages_map = {}
    if purls_to_fetch:
        existing_packages = Package.objects.filter(purl__in=purls_to_fetch, service=default_service)
        packages_map = {pkg.purl: pkg for pkg in existing_packages}

        missing_purls = purls_to_fetch - set(packages_map.keys())
        if missing_purls:
            new_packages = [Package(purl=purl, service=default_service) for purl in missing_purls]
            Package.objects.bulk_create(new_packages, ignore_conflicts=True)
            refreshed = Package.objects.filter(purl__in=missing_purls, service=default_service)
            packages_map.update({pkg.purl: pkg for pkg in refreshed})

    for pkg_status_a, pkg_status_b in zip_longest(yaml_data_a_blob or [], yaml_data_b_blob or []):
        pkg_a = pkg_b = None

        if pkg_status_a and pkg_status_a.get("purl"):
            core_purl_a = get_core_purl(pkg_status_a["purl"])
            pkg_a = packages_map.get(str(core_purl_a))

        if pkg_status_b and pkg_status_b.get("purl"):
            core_purl_b = get_core_purl(pkg_status_b["purl"])
            pkg_b = packages_map.get(str(core_purl_b))

        if change_type == "A":
            if pkg_status_b and pkg_b:
                notes_to_create.append((pkg_b, pkg_status_b))

        elif change_type == "M":
            if pkg_status_a and not pkg_status_b and pkg_a:
                notes_to_delete.append((pkg_a, pkg_status_a))

            elif pkg_status_b and not pkg_status_a and pkg_b:
                notes_to_create.append((pkg_b, pkg_status_b))

            elif pkg_status_a and pkg_status_b and pkg_b:
                notes_to_update.append((pkg_b, pkg_status_a, pkg_status_b))

        elif change_type == "D":
            if pkg_status_a and pkg_a:
                notes_to_delete.append((pkg_a, pkg_status_a))

        else:
            logger(f"Unknown change_type: {change_type}", level=logging.ERROR)

    if notes_to_create:
        bulk_create_notes(notes_to_create)
    if notes_to_update:
        bulk_update_notes(notes_to_update)
    if notes_to_delete:
        bulk_delete_notes(notes_to_delete)


def bulk_create_notes(notes_to_create):
    """Bulk create notes and federate activities"""
    if not notes_to_create:
        return

    notes_by_pkg = {}
    note_objects_to_create = []

    for pkg, note_dict in notes_to_create:
        content = saneyaml.dump(note_dict)
        if pkg not in notes_by_pkg:
            notes_by_pkg[pkg] = []
        notes_by_pkg[pkg].append(content)

    existing_notes = set()
    for pkg, contents in notes_by_pkg.items():
        existing = Note.objects.filter(acct=pkg.acct, content__in=contents).values_list(
            "content", flat=True
        )
        existing_notes.update(existing)

    pkg_note_pairs = []
    activities_to_federate = []

    for pkg, note_dict in notes_to_create:
        content = saneyaml.dump(note_dict)

        if content not in existing_notes:
            note = Note(acct=pkg.acct, content=content)
            note_objects_to_create.append(note)
            pkg_note_pairs.append((pkg, note))

    if note_objects_to_create:
        created_notes = Note.objects.bulk_create(note_objects_to_create)

        through_objects = []
        for i, (pkg, _) in enumerate(pkg_note_pairs):
            note = created_notes[i]
            through_objects.append(Package.notes.through(package_id=pkg.id, note_id=note.id))

        Package.notes.through.objects.bulk_create(through_objects, ignore_conflicts=True)

        for pkg, note in zip([p for p, _ in pkg_note_pairs], created_notes):
            if pkg.followers_inboxes:
                create_activity = CreateActivity(actor=pkg.to_ap, object=note.to_ap)
                activities_to_federate.append(
                    {
                        "targets": pkg.followers_inboxes,
                        "body": json.dumps(create_activity.to_ap()),
                        "key_id": pkg.key_id,
                    }
                )

    for pkg, note_dict in notes_to_create:
        content = saneyaml.dump(note_dict)
        if content in existing_notes:
            note = Note.objects.get(acct=pkg.acct, content=content)
            pkg.notes.add(note)

            # Still need to federate for existing notes
            if pkg.followers_inboxes:
                create_activity = CreateActivity(actor=pkg.to_ap, object=note.to_ap)
                activities_to_federate.append(
                    {
                        "targets": pkg.followers_inboxes,
                        "body": json.dumps(create_activity.to_ap()),
                        "key_id": pkg.key_id,
                    }
                )

    if activities_to_federate:
        Activity.bulk_federate(activities_to_federate)


def bulk_update_notes(notes_to_update):
    """Bulk update notes and federate activities"""
    if not notes_to_update:
        return

    actual_updates = []
    for pkg, old_note_dict, new_note_dict in notes_to_update:
        if old_note_dict != new_note_dict:
            actual_updates.append((pkg, old_note_dict, new_note_dict))

    if not actual_updates:
        return

    query_conditions = Q()
    update_mapping = {}

    for pkg, old_note_dict, new_note_dict in actual_updates:
        old_content = saneyaml.dump(old_note_dict)
        new_content = saneyaml.dump(new_note_dict)
        query_conditions |= Q(acct=pkg.acct, content=old_content)
        update_mapping[(pkg.acct, old_content)] = new_content

    notes_to_update_qs = Note.objects.filter(query_conditions)
    existing_notes = list(notes_to_update_qs)

    if not existing_notes:
        return

    when_clauses = []
    activities_to_federate = []
    note_id_to_pkg = {}

    for note in existing_notes:
        key = (note.acct, note.content)
        if key in update_mapping:
            new_content = update_mapping[key]
            when_clauses.append(When(id=note.id, then=Value(new_content)))

            for pkg, old_note_dict, new_note_dict in actual_updates:
                if pkg.acct == note.acct and saneyaml.dump(old_note_dict) == note.content:
                    note_id_to_pkg[note.id] = (pkg, new_note_dict)
                    break

    if when_clauses:
        Note.objects.filter(id__in=[note.id for note in existing_notes]).update(
            content=Case(*when_clauses, output_field=TextField())
        )

        for note in existing_notes:
            if note.id in note_id_to_pkg:
                pkg, new_note_dict = note_id_to_pkg[note.id]
                if pkg.followers_inboxes:
                    note.content = saneyaml.dump(new_note_dict)
                    update_activity = UpdateActivity(actor=pkg.to_ap, object=note.to_ap)
                    activities_to_federate.append(
                        {
                            "targets": pkg.followers_inboxes,
                            "body": json.dumps(update_activity.to_ap()),
                            "key_id": pkg.key_id,
                        }
                    )

        if activities_to_federate:
            Activity.bulk_federate(activities_to_federate)


def bulk_delete_notes(notes_to_delete):
    """Bulk delete notes (soft delete) and federate activities"""
    if not notes_to_delete:
        return

    query_conditions = Q()
    delete_mapping = {}

    for pkg, note_dict in notes_to_delete:
        content = saneyaml.dump(note_dict)
        query_conditions |= Q(acct=pkg.acct, content=content)
        delete_mapping[(pkg.acct, content)] = pkg

    notes_to_delete_qs = Note.objects.filter(query_conditions)
    existing_notes = list(notes_to_delete_qs.select_related())

    if not existing_notes:
        return

    activities_to_federate = []
    notes_to_soft_delete = []

    for note in existing_notes:
        key = (note.acct, note.content)
        if key in delete_mapping:
            pkg = delete_mapping[key]
            notes_to_soft_delete.append(note.id)
            note_ap = note.to_ap

            if pkg.followers_inboxes:
                deleted_activity = DeleteActivity(actor=pkg.to_ap, object=note_ap)
                activities_to_federate.append(
                    {
                        "targets": pkg.followers_inboxes,
                        "body": json.dumps(deleted_activity.to_ap()),
                        "key_id": pkg.key_id,
                    }
                )

    if notes_to_soft_delete:
        Note.objects.filter(id__in=notes_to_soft_delete).delete()

        if activities_to_federate:
            Activity.bulk_federate(activities_to_federate)
