#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#
from unittest.mock import PropertyMock
from unittest.mock import call
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from fedcode_test_utils import mute_post_save_signal  # NOQA

from aboutcode.hashid import get_core_purl
from fedcode.models import Note
from fedcode.models import Package
from fedcode.models import Repository
from fedcode.models import Service
from fedcode.models import Vulnerability
from fedcode.pipelines.sync_vulnerablecode import SyncVulnerableCode
from fedcode.pipelines.sync_vulnerablecode import note_handler
from fedcode.pipelines.sync_vulnerablecode import pkg_handler
from fedcode.pipelines.sync_vulnerablecode import vul_handler

TEST_REPO_1_PATH = "/home/ziad-hany/PycharmProjects/vul-sample"


@pytest.fixture
def service(db):
    user = User.objects.create(
        username="vcio",
        email="vcio@nexb.com",
        password="complex-password",
    )
    return Service.objects.create(
        user=user,
    )


@pytest.fixture
def mock_latest_commit_hexsha(monkeypatch):
    """
    Fixture to override only repo.head.commit.hexsha while keeping
    the rest of the git repo behavior intact.
    """

    def _mock(repo_instance, hexsha: str):
        """
        repo_instance: a Repository model instance
        hexsha: the fake hexsha to return for latest commit
        """
        real_repo = repo_instance.git_repo_obj  # use real GitPython repo

        # Patch only the hexsha property
        type(real_repo.head.commit).hexsha = PropertyMock(return_value=hexsha)

        return real_repo

    return _mock


@pytest.fixture
def repo(db, service, mute_post_save_signal):
    """Simple Git Repository"""
    return Repository.objects.create(
        url="https://github.com/ziadhany/vul-sample",
        path=TEST_REPO_1_PATH,
        admin=service,
    )


@pytest.fixture
def vul_changes():
    return {"create": [], "update": [], "delete": set()}


@pytest.fixture
def pkg_changes():
    return {"create": [], "update": [], "delete": set()}


@pytest.fixture
def example_notes():
    return [
        {
            "purl": "pkg:alpine/ansible@2.10.1-r0?arch=aarch64&distroversion=edge&reponame=community",
            "affected_by_vulnerabilities": [],
            "fixing_vulnerabilities": ["VCID-r7zs-rzfz-aaap"],
        },
        {
            "purl": "pkg:alpine/ansible@2.10.1-r0?arch=armhf&distroversion=edge&reponame=community",
            "affected_by_vulnerabilities": ["VCID-r7zs-rzfz-aaap"],
            "fixing_vulnerabilities": [],
        },
    ]

def test_added_vulnerability(repo, vul_changes):
    vul_handler("A", repo, None, {"vulnerability_id": "VCID-1234"}, None, vul_changes)
    assert len(vul_changes["create"]) == 1
    vuln = vul_changes["create"][0]
    assert isinstance(vuln, Vulnerability)
    assert vuln.id == "VCID-1234"
    assert vuln.repo == repo


def test_modified_vulnerability_changed_id(repo, vul_changes):
    vul_handler(
        "M",
        repo,
        {"vulnerability_id": "VCID-1111"},
        {"vulnerability_id": "VCID-2222"},
        None,
        vul_changes,
    )

    assert ("VCID-1111", repo) in vul_changes["delete"]
    assert ("VCID-2222", repo) in vul_changes["update"]


def test_modified_vulnerability_same_id(repo, vul_changes):
    vul_handler(
        "M",
        repo,
        {"vulnerability_id": "VCID-1111"},
        {"vulnerability_id": "VCID-1111"},
        None,
        vul_changes,
    )

    assert not vul_changes["delete"]
    assert ("VCID-1111", repo) in vul_changes["update"]


def test_deleted_vulnerability(repo, vul_changes):
    vul_handler("D", repo, {"vulnerability_id": "VCID-3333"}, None, None, vul_changes)
    assert ("VCID-3333", repo) in vul_changes["delete"]


def test_added_packages(service, pkg_changes):
    yaml_data_b_blob = ["pkg:pypi/django@3.2.5", "pkg:pypi/requests@2.28.1"]

    pkg_handler("A", service, None, yaml_data_b_blob, None, pkg_changes)

    assert len(pkg_changes["create"]) == 2
    created = [pkg.purl for pkg in pkg_changes["create"]]
    assert get_core_purl("pkg:pypi/django@3.2.5") in created
    assert get_core_purl("pkg:pypi/requests@2.28.1") in created


def test_modified_packages(service, pkg_changes):
    yaml_data_a_blob = ["pkg:pypi/django@3.2.5", "pkg:pypi/requests@2.27.0"]
    yaml_data_b_blob = ["pkg:pypi/django@4.0.0", "pkg:pypi/requests@2.28.1"]

    pkg_handler("M", service, yaml_data_a_blob, yaml_data_b_blob, None, pkg_changes)

    assert len(pkg_changes["update"]) == 2
    updates = [(a, b) for (a, b, _) in pkg_changes["update"]]
    assert (
        get_core_purl("pkg:pypi/django@3.2.5"),
        get_core_purl("pkg:pypi/django@4.0.0"),
    ) in updates
    assert (
        get_core_purl("pkg:pypi/requests@2.27.0"),
        get_core_purl("pkg:pypi/requests@2.28.1"),
    ) in updates


def test_deleted_packages(service, pkg_changes):
    yaml_data_a_blob = ["pkg:pypi/flask@2.0.0", "pkg:pypi/urllib3@1.26.0"]

    pkg_handler("D", service, yaml_data_a_blob, None, None, pkg_changes)

    assert len(pkg_changes["delete"]) == 2
    deletes = [(p, svc) for (p, svc) in pkg_changes["delete"]]
    assert (get_core_purl("pkg:pypi/flask@2.0.0"), service) in deletes
    assert (get_core_purl("pkg:pypi/urllib3@1.26.0"), service) in deletes


def test_note_handler_add(service, example_notes):
    with patch("fedcode.pipelines.sync_vulnerablecode.bulk_create_notes") as mock_create:
        note_handler("A", service, None, example_notes, None)
        assert mock_create.called
        args, _ = mock_create.call_args
        notes_to_create = args[0]
        assert len(notes_to_create) == len(example_notes)
        pkg = Package.objects.get(purl="pkg:alpine/ansible")
        expected = [
            (
                pkg,
                {
                    "affected_by_vulnerabilities": [],
                    "fixing_vulnerabilities": ["VCID-r7zs-rzfz-aaap"],
                    "purl": "pkg:alpine/ansible@2.10.1-r0?arch=aarch64&distroversion=edge&reponame=community",
                },
            ),
            (
                pkg,
                {
                    "affected_by_vulnerabilities": ["VCID-r7zs-rzfz-aaap"],
                    "fixing_vulnerabilities": [],
                    "purl": "pkg:alpine/ansible@2.10.1-r0?arch=armhf&distroversion=edge&reponame=community",
                },
            ),
        ]
        assert notes_to_create == expected


def test_note_handler_modify(service, example_notes):
    old_notes = example_notes[:1]  # first note only
    new_notes = example_notes[1:]  # second note only

    with patch("fedcode.pipelines.sync_vulnerablecode.bulk_update_notes") as mock_update, patch(
        "fedcode.pipelines.sync_vulnerablecode.bulk_create_notes"
    ) as mock_create, patch(
        "fedcode.pipelines.sync_vulnerablecode.bulk_delete_notes"
    ) as mock_delete:

        note_handler("M", service, old_notes, new_notes, None)
        pkg = Package.objects.get(purl="pkg:alpine/ansible")
        assert mock_update.call_args_list == [
            call(
                [
                    (
                        pkg,
                        {
                            "purl": "pkg:alpine/ansible@2.10.1-r0?arch=aarch64&distroversion=edge&reponame=community",
                            "affected_by_vulnerabilities": [],
                            "fixing_vulnerabilities": ["VCID-r7zs-rzfz-aaap"],
                        },
                        {
                            "purl": "pkg:alpine/ansible@2.10.1-r0?arch=armhf&distroversion=edge&reponame=community",
                            "affected_by_vulnerabilities": ["VCID-r7zs-rzfz-aaap"],
                            "fixing_vulnerabilities": [],
                        },
                    )
                ]
            )
        ]

        assert mock_delete.called == False
        assert mock_create.called == False
        assert mock_update.called


def test_note_handler_delete(service, example_notes):
    with patch("fedcode.pipelines.sync_vulnerablecode.bulk_delete_notes") as mock_delete:
        note_handler("D", service, example_notes, None, None)
        assert mock_delete.called
        args, _ = mock_delete.call_args
        notes_to_delete = args[0]
        assert len(notes_to_delete) == len(example_notes)


@pytest.mark.skip(reason="A real Git repository is needed to test the pipelines.")
@pytest.mark.django_db
def test_simple_importer(service, repo, mock_latest_commit_hexsha, mute_post_save_signal):
    repo.path = TEST_REPO_1_PATH
    importer = SyncVulnerableCode()
    commits = [
        # (commit, last_imported_commit, note_count, vuln_count, pkg_count)
        (
            "f7cd453ff1ef29a539723c44f82bcc582dac13b1",
            None,
            28,
            6,
            3,
        ),  # vuln_count is 7, but one of them is duplicated.
        ("d2115ebdc64341f5b9169e42c9edde9002898b3b", "f7cd453ff1ef29a539723c44f82bcc582dac13b1", 45, 6, 3),
        ("d2115ebdc64341f5b9169e42c9edde9002898b3b", None, 0, 0, 0),
        ("275987c1d758155e782b7fe0539d7089d4e618ea", None, 0, 0, 0),
    ]

    for commit, last_imported_commit, note_count, vuln_count, pkg_count in commits:
        repo.last_imported_commit = last_imported_commit
        repo.save()

        mock_latest_commit_hexsha(repo, hexsha=commit)
        importer.execute()

        assert Note.objects.count() == note_count
        assert Vulnerability.objects.count() == vuln_count
        assert Package.objects.count() == pkg_count
