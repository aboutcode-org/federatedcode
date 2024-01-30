#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import json

import pytest

from fedcode.activitypub import AP_CONTEXT
from fedcode.activitypub import create_activity_obj
from fedcode.models import Follow
from fedcode.models import Note
from fedcode.models import Repository
from fedcode.models import Review

from .test_models import follow
from .test_models import mute_post_save_signal
from .test_models import note
from .test_models import package
from .test_models import person
from .test_models import repo
from .test_models import service
from .test_models import vulnerability


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


# @pytest.mark.django_db
# def test_person_sync_repo(service, repo):
#     payload = json.dumps(
#         {
#             **AP_CONTEXT,
#             "type": "Sync",
#             "actor": f"https://127.0.0.1:8000/users/@{service.user.username}",
#             "object": {
#                 "type": "Repository",
#                 "id": f"https://127.0.0.1:8000/repository/{repo.id}/",
#             },
#         }
#     )
#
#     activity = create_activity_obj(payload)
#     sync_activity = activity.handler()
