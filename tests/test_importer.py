#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#
import pytest
from django.contrib.auth.models import User
from fedcode_test_utils import mute_post_save_signal  # NOQA

from fedcode.importer import Importer
from fedcode.models import Note
from fedcode.models import Package
from fedcode.models import Repository
from fedcode.models import Service
from fedcode.models import Vulnerability


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
def repo(db, service, mute_post_save_signal):
    """Simple Git Repository"""
    return Repository.objects.create(
        url="https://github.com/nexB/fake-repo",
        path="./review/tests/test_data/test_git_repo_v1",
        admin=service,
    )


@pytest.mark.skip(reason="Need a real git repo to test the importer")
@pytest.mark.django_db
def test_simple_importer(service, repo, mute_post_save_signal):
    # just add all packages and vulnerabilities
    repo.path = "/home/ziad/vul-sample/repo1"
    importer = Importer(repo, service)
    importer.run()

    assert Note.objects.count() > 1
    assert Vulnerability.objects.count() > 1
    assert Package.objects.count() > 1
    assert repo.last_imported_commit

    note_n = Note.objects.count()
    vul_n = Vulnerability.objects.count()
    purl_n = Package.objects.count()
    last_imported_commit = repo.last_imported_commit

    # Run importer again without add any new data
    importer = Importer(repo, service)
    importer.run()

    assert note_n == Note.objects.count()
    assert vul_n == Vulnerability.objects.count()
    assert purl_n == Package.objects.count()
    assert last_imported_commit == repo.last_imported_commit

    # Edit last_imported_commit
    repo.last_imported_commit = "c8de84af0a7c11bf151e96142ce711824648ec41"
    repo.save()
    importer = Importer(repo, service)
    importer.run()


@pytest.mark.skip(reason="Need a real git repo to test the importer")
@pytest.mark.django_db
def test_complex_importer(service, repo, mute_post_save_signal):
    # repo with 1 commit
    repo.path = "/home/ziad/vul-sample/repo1"
    importer = Importer(repo, service)
    importer.run()

    assert Note.objects.count() > 1
    assert Vulnerability.objects.count() > 1
    assert Package.objects.count() > 1
    assert repo.last_imported_commit

    note_n = Note.objects.count()
    vul_n = Vulnerability.objects.count()
    purl_n = Package.objects.count()
    last_imported_commit = repo.last_imported_commit

    # Run importer again without add any new data
    # the same repo with 2 commit ( after pull )
    repo.path = "/home/ziad/vul-sample/repo2"
    importer = Importer(repo, service)
    importer.run()

    assert note_n > Note.objects.count()
    assert vul_n > Vulnerability.objects.count()
    assert purl_n > Package.objects.count()

    # Edit last_imported_commit
    repo.last_imported_commit = "9c3ccee39baef6017d9152367402de9909eadd72"
    repo.save()
    importer = Importer(repo, service)
    importer.run()
