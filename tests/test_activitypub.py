#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#
import json

import pytest
from django.contrib.auth.models import User
from fedcode_test_utils import mute_post_save_signal  # NOQA

from fedcode.activitypub import AP_CONTEXT
from fedcode.activitypub import Activity
from fedcode.activitypub import CreateActivity
from fedcode.activitypub import DeleteActivity
from fedcode.activitypub import SyncActivity
from fedcode.activitypub import UpdateActivity
from fedcode.activitypub import create_activity_obj
from fedcode.models import Follow
from fedcode.models import Note
from fedcode.models import Package
from fedcode.models import Person
from fedcode.models import Repository
from fedcode.models import Review
from fedcode.models import Service
from fedcode.models import SyncRequest
from fedcode.models import Vulnerability


@pytest.fixture
def service(db):
    user = User.objects.create(username="vcio", email="vcio@nexb.com", password="complex-password")
    return Service.objects.create(user=user)


@pytest.fixture
def package(db, service):
    return Package.objects.create(purl="pkg:maven/org.apache.logging", service=service)


@pytest.fixture
def person(db):
    user1 = User.objects.create(username="ziad", email="ziad@nexb.com", password="complex-password")
    return Person.objects.create(user=user1, summary="Hello World", public_key="PUBLIC_KEY")


@pytest.fixture
def repo(db, service, mute_post_save_signal):
    """Simple Git Repository"""
    return Repository.objects.create(
        url="https://github.com/nexB/fake-repo",
        path="./review/tests/test_data/test_git_repo_v1",
        admin=service,
    )


@pytest.fixture
def vulnerability(db, repo):
    return Vulnerability.objects.create(id="VCID-1155-4sem-aaaq", repo=repo)


@pytest.fixture
def note(db):
    return Note.objects.create(acct="ziad@127.0.0.1:8000", content="Comment #1")


@pytest.fixture
def follow(db, package, person):
    return Follow.objects.create(package=package, person=person)


@pytest.fixture
def fake_service(db):
    user = User.objects.create(
        username="fake_service",
        email="vcio@nexb.com",
        password="complex-password",
    )
    return Service.objects.create(user=user)


@pytest.fixture
def pkg_note(db, package):
    return Note.objects.create(
        acct=package.acct,
        content="purl: "
        "pkg:maven/org.apache.logging@2.23-r0?arch=aarch64&distroversion=edge&reponame=community\n"
        "         affected_by_vulnerabilities: ....",
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


@pytest.mark.django_db
def test_person_create_note(person):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Create",
            "actor": f"https://127.0.0.1:8000/api/v0/users/@{person.user.username}",
            "object": {
                "type": "Note",
                "content": "we should fix this purl",
            },
        }
    )

    activity = create_activity_obj(payload)
    create_activity = activity.handler()
    assert Note.objects.count() == 1
    note = Note.objects.get(acct=person.acct, content="we should fix this purl")
    assert json.loads(create_activity.content) == {
        "Location": f"https://127.0.0.1:8000/notes/{note.id}"
    }
    assert create_activity.status_code == 201


@pytest.mark.django_db
def test_person_create_review(person, vulnerability, repo):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Create",
            "actor": f"https://127.0.0.1:8000/api/v0/users/@ziad",
            "object": {
                "type": "Review",
                "headline": "review vulnerablecode-data VCID-0000-0000-0000",
                "repository": f"https://127.0.0.1:8000/repository/{repo.id}/",
                "filepath": "/apache/httpd/VCID-0000-0000-0000.yml",
                "commit": "104ccd6a7a41329b2953c96e52792a3d6a9ad8e5",
                "content": "diff text",
            },
        }
    )

    activity = create_activity_obj(payload)
    create_activity = activity.handler()
    assert Review.objects.count() == 1
    review = Review.objects.get(
        headline="review vulnerablecode-data VCID-0000-0000-0000",
        author=person,
        repository=repo,
        data="diff text",
        filepath="/apache/httpd/VCID-0000-0000-0000.yml",
        commit="104ccd6a7a41329b2953c96e52792a3d6a9ad8e5",
        status=0,
    )
    assert json.loads(create_activity.content) == {
        "Location": f"https://127.0.0.1:8000/reviews/{review.id}/"
    }
    assert create_activity.status_code == 201


@pytest.mark.django_db
def test_purl_create_note(package, service):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Create",
            "actor": f"https://127.0.0.1:8000/api/v0/purls/@{package.purl}/",
            "object": {
                "type": "Note",
                "content": "we should fix this purl",
            },
        }
    )
    activity = create_activity_obj(payload)
    create_activity = activity.handler()
    note = Note.objects.get(acct=package.acct, content="we should fix this purl")
    assert json.loads(create_activity.content) == {
        "Location": f"https://127.0.0.1:8000/notes/{note.id}"
    }
    assert create_activity.status_code == 201


@pytest.mark.django_db
def test_service_create_repo(service):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Create",
            "actor": f"https://127.0.0.1:8000/api/v0/users/@{service.user.username}",
            "object": {
                "type": "Repository",
                "url": "https://github.com/nexB/vulnerablecode-data",
            },
        }
    )
    activity = create_activity_obj(payload)
    create_activity = activity.handler()
    assert Repository.objects.count() == 1
    repo = Repository.objects.get(
        url="https://github.com/nexB/vulnerablecode-data",
        admin=service,
    )
    assert json.loads(create_activity.content) == {
        "Location": f"https://127.0.0.1:8000/repository/{repo.id}/"
    }
    assert create_activity.status_code == 201


@pytest.mark.django_db
def test_person_follow_package(person, package):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Follow",
            "actor": f"https://127.0.0.1:8000/api/v0/users/@{person.user.username}",
            "object": {
                "type": "Package",
                "id": f"https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
            },
        }
    )

    activity = create_activity_obj(payload)
    follow_activity = activity.handler()
    assert Follow.objects.get(person=person, package=package)
    assert Follow.objects.count() == 1


@pytest.mark.django_db
def test_person_delete_note(person, note):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Delete",
            "actor": f"https://127.0.0.1:8000/api/v0/users/@{person.user.username}",
            "object": {
                "type": "Note",
                "id": f"https://127.0.0.1:8000/notes/{note.id}",
            },
        }
    )

    activity = create_activity_obj(payload)
    delete_activity = activity.handler()
    assert Note.objects.count() == 0
    assert json.loads(delete_activity.content) == {
        "message": "The object has been deleted successfully"
    }
    assert delete_activity.status_code == 200


@pytest.mark.django_db
def test_person_delete_note2(person, note):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Delete",
            "actor": f"https://127.0.0.1:8000/api/v0/users/@{person.user.username}",
            "object": {
                "type": "Note",
                "id": f"https://127.0.0.1:8000/notes/{note.id}",
            },
        }
    )

    activity = create_activity_obj(payload)
    delete_activity = activity.handler()
    assert Note.objects.count() == 0


@pytest.mark.django_db
def test_person_update_note(person, note):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Update",
            "actor": f"https://127.0.0.1:8000/api/v0/users/@{person.user.username}",
            "object": {
                "id": f"https://127.0.0.1:8000/notes/{note.id}",
                "type": "Note",
                "content": "Hello World!",
            },
        }
    )

    activity = create_activity_obj(payload)
    update_activity = activity.handler()
    assert Note.objects.count() == 1
    note = Note.objects.get(id=note.id)
    assert note.content == "Hello World!"
    assert json.loads(update_activity.content) == note.to_ap
    assert update_activity.status_code == 200


@pytest.mark.django_db
def test_person_unfollow_package(person, package, follow):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "UnFollow",
            "actor": f"https://127.0.0.1:8000/api/v0/users/@{person.user.username}",
            "object": {
                "type": "Package",
                "id": f"https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
            },
        }
    )

    activity = create_activity_obj(payload)
    follow_activity = activity.handler()
    assert Follow.objects.count() == 0


@pytest.mark.django_db
def test_get_actor_permissions(
    person, package, service, repo, note, review, pkg_note, fake_service
):
    assert Activity.get_actor_permissions(person, note)() == {
        CreateActivity,
        UpdateActivity,
        DeleteActivity,
    }
    assert Activity.get_actor_permissions(person, review)() == {
        CreateActivity,
        UpdateActivity,
        DeleteActivity,
    }
    assert Activity.get_actor_permissions(service, repo)() == {
        CreateActivity,
        UpdateActivity,
        DeleteActivity,
        SyncActivity,
    }
    assert Activity.get_actor_permissions(package, pkg_note)() == {
        CreateActivity,
        UpdateActivity,
        DeleteActivity,
    }

    note.acct = "fake_person@127.0.0.2"
    assert Activity.get_actor_permissions(person, note)() == {CreateActivity, None}

    repo.admin = fake_service
    assert Activity.get_actor_permissions(service, repo)() == {CreateActivity, None}

    assert Activity.get_actor_permissions(package, note)() == {CreateActivity, None}


@pytest.mark.django_db
def test_service_sync_repo(service, repo):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Sync",
            "actor": f"https://127.0.0.1:8000/api/v0/users/@{service.user.username}",
            "object": {
                "type": "Repository",
                "id": f"https://127.0.0.1:8000/repository/{repo.id}/",
            },
        }
    )

    activity = create_activity_obj(payload)
    sync_activity = activity.handler()
    assert SyncRequest.objects.all().count() == 1
