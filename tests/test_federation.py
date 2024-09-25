#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#
import json
from unittest import mock

import pytest
from django.contrib.auth.models import User

from fedcode.activitypub import AP_CONTEXT
from fedcode.activitypub import create_activity_obj
from fedcode.models import Follow
from fedcode.models import Note
from fedcode.models import Package
from fedcode.models import Person
from fedcode.models import RemoteActor
from fedcode.models import Service
from fedcode.utils import file_data


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
def remote_person(db):
    remote_user1 = RemoteActor.objects.create(url="127.0.0.2", username="remote-ziad")
    return Person.objects.create(remote_actor=remote_user1)


@mock.patch("httpx.Client")
@mock.patch("requests.get")
@pytest.mark.django_db
def test_remote_person_follow_package(mock_get, _, package):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Follow",
            "actor": "https://127.0.0.2:8000/api/v0/users/@ziad",
            "object": {
                "type": "Package",
                "id": "https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
            },
            "to": ["https://127.0.0.2:8000/api/v0/users/@ziad"],
        }
    )

    mock_request_remote_person_webfinger = mock.Mock(status_code=200)
    mock_request_remote_person_webfinger.json.return_value = file_data(
        "tests/test_data/mock_request_remote_person_webfinger.json"
    )

    mock_request_remote_person = mock.Mock(status_code=200)
    mock_request_remote_person.json.return_value = file_data(
        "tests/test_data/mock_request_remote_person.json"
    )

    mock_request_server_to_server = mock.Mock(status_code=200)

    mock_get.side_effect = [
        mock_request_remote_person_webfinger,
        mock_request_remote_person,
        mock_request_server_to_server,
    ]

    activity = create_activity_obj(payload)
    activity_response = activity.handler()
    remote_person = RemoteActor.objects.get(
        url="https://127.0.0.2:8000/api/v0/users/@ziad", username="ziad"
    ).person

    assert Follow.objects.get(person=remote_person, package=package)
    assert Follow.objects.count() == 1


@mock.patch("httpx.Client")
@mock.patch("requests.get")
@pytest.mark.django_db
def test_person_follow_remote_package(mock_get, _, person):
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Follow",
            "actor": f"https://127.0.0.1:8000/api/v0/users/@{person.user.username}",
            "object": {
                "type": "Package",
                "id": "https://127.0.0.2:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
            },
            "to": [f"https://127.0.0.1:8000/api/v0/users/@{person.user.username}"],
        }
    )

    activity = create_activity_obj(payload)
    mock_request_remote_package_webfinger = mock.Mock(status_code=200)
    mock_request_remote_package_webfinger.json.return_value = file_data(
        "tests/test_data/mock_request_remote_purl_webfinger.json"
    )

    mock_request_remote_package = mock.Mock(status_code=200)
    mock_request_remote_package.json.return_value = file_data(
        "tests/test_data/mock_request_remote_purl.json"
    )
    mock_request_server_to_server = mock.Mock(status_code=200)

    mock_get.side_effect = [
        mock_request_remote_package_webfinger,
        mock_request_remote_package,
        mock_request_server_to_server,
    ]

    follow_activity = activity.handler()
    remote_package = RemoteActor.objects.get(
        url="https://127.0.0.2:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
        username="vcio",
    ).package

    assert Follow.objects.get(person=person, package=remote_package)
    assert Follow.objects.count() == 1


@pytest.mark.django_db
@mock.patch("httpx.Client")
def test_package_with_remote_follower_create_note(mock_get, package, remote_person):
    Follow.objects.create(package=package, person=remote_person)
    payload = json.dumps(
        {
            **AP_CONTEXT,
            "type": "Create",
            "actor": f"https://127.0.0.1:8000/api/v0/purls/@{package.purl}/",
            "object": {
                "type": "Note",
                "content": "we should fix this purl",
            },
            "to": ["https://127.0.0.1/remote-user/"],
        }
    )
    activity = create_activity_obj(payload)
    create_activity = activity.handler()
    note = Note.objects.get(acct=package.acct, content="we should fix this purl")
    assert json.loads(create_activity.content) == {
        "Location": f"https://127.0.0.1:8000/notes/{note.id}"
    }
    assert create_activity.status_code == 201

    mock_get.status_code.return_value = 200
    mock_get.json.return_value = {}
