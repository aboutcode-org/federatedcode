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

from fedcode.models import Follow
from fedcode.models import Note
from fedcode.models import Package
from fedcode.models import Person
from fedcode.models import RemoteActor
from fedcode.models import Repository
from fedcode.models import Reputation
from fedcode.models import Review
from fedcode.models import Service
from fedcode.models import Vulnerability


@pytest.fixture
def person(db):
    user1 = User.objects.create(username="ziad", email="ziad@nexb.com", password="complex-password")
    return Person.objects.create(user=user1, summary="Hello World", public_key="PUBLIC_KEY")


@pytest.fixture
def remote_person(db):
    remote_user1 = RemoteActor.objects.create(url="127.0.0.2", username="remote-ziad")
    return Person.objects.create(remote_actor=remote_user1)


def test_person(person):
    assert person.user.username == "ziad"
    assert person.user.email == "ziad@nexb.com"
    assert person.summary == "Hello World"
    assert person.public_key == "PUBLIC_KEY"


def test_remote_person(remote_person):
    assert remote_person.remote_actor.url == "127.0.0.2"
    assert remote_person.remote_actor.username == "remote-ziad"


@pytest.fixture
def package(db, service):
    return Package.objects.create(purl="pkg:maven/org.apache.logging", service=service)


@pytest.fixture
def service(db):
    user = User.objects.create(username="vcio", email="vcio@nexb.com", password="complex-password")
    return Service.objects.create(user=user)


def test_purl(package, service):
    assert package.service == service
    assert package.purl == "pkg:maven/org.apache.logging"
    assert Package.objects.count() == 1


@pytest.fixture
def note(db):
    return Note.objects.create(
        acct="ziad@127.0.0.1:8000",
        content="Comment #1",
    )


@pytest.fixture
def follow(db, package, person):
    return Follow.objects.create(package=package, person=person)


def test_follow(follow, package, person):
    assert follow.package.purl == package.purl
    assert follow.person.user == person.user


@pytest.fixture
def repo(db, service, mute_post_save_signal):
    """Simple Git Repository"""
    return Repository.objects.create(
        url="https://github.com/nexB/fake-repo",
        path="./review/tests/test_data/test_git_repo_v1",
        admin=service,
    )


@pytest.fixture
def review(db, repo, person):
    return Review.objects.create(
        headline="Review title 1",
        author=person,
        repository=repo,
        filepath="/apache/httpd/VCID-1a68-fd5t-aaam.yml",
        data="text diff",
        commit="49d8c5fd4bea9488186a832b13ebdc83484f1b6a",
    )


def test_review(review, person, repo):
    assert review.headline == "Review title 1"
    assert review.author == person
    assert review.repository == repo
    assert review.filepath == "/apache/httpd/VCID-1a68-fd5t-aaam.yml"
    assert review.data == "text diff"
    assert review.status == 0
    assert review.commit == "49d8c5fd4bea9488186a832b13ebdc83484f1b6a"


@pytest.fixture
def rep(db, note):
    return Reputation.objects.create(
        voter="ziad@vcio",
        positive=True,
        content_object=note,
    )


def test_reputation(rep, note):
    assert rep.voter == "ziad@vcio"
    assert rep.positive is True
    assert rep.content_object == note


@pytest.fixture
def vulnerability(db, repo):
    return Vulnerability.objects.create(
        id="VCID-1155-4sem-aaaq",
        repo=repo,
    )


def test_vulnerability(vulnerability, repo):
    assert vulnerability.id == "VCID-1155-4sem-aaaq"
    assert vulnerability.repo == repo
