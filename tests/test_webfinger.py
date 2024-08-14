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
from django.test import Client

from fedcode.models import Package
from fedcode.models import Person
from fedcode.models import Service
from fedcode.utils import generate_webfinger
from federatedcode.settings import FEDERATEDCODE_DOMAIN


@pytest.fixture
def service(db):
    user = User.objects.create(username="vcio", email="vcio@nexb.com", password="complex-password")
    return Service.objects.create(user=user)


@pytest.fixture
def package(db, service):
    return Package.objects.create(purl="pkg:maven/org.apache.logging", service=service)


@pytest.fixture
def person(db):
    user1 = User.objects.create(
        username="ziad",
        email="ziad@nexb.com",
        password="complex-password",
    )
    return Person.objects.create(user=user1, summary="Hello World", public_key="PUBLIC_KEY")


@pytest.mark.django_db
def test_webfinger(person, service, package):
    client = Client()
    person_acct = "acct:" + generate_webfinger(person.user.username)
    response_person = client.get(f"/.well-known/webfinger?resource={person_acct}")

    service_acct = "acct:" + generate_webfinger(service.user.username)
    response_service = client.get(f"/.well-known/webfinger?resource={service_acct}")

    package_acct = "acct:" + generate_webfinger(package.purl)
    response_purl = client.get(f"/.well-known/webfinger?resource={package_acct}")

    assert json.loads(response_person.content) == {
        "subject": person_acct,
        "links": [
            {
                "rel": "https://webfinger.net/rel/profile-page",
                "type": "text/html",
                "href": f"https://{FEDERATEDCODE_DOMAIN}/users/@{person.user.username}",
            },
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": f"https://{FEDERATEDCODE_DOMAIN}/api/v0/users/@{person.user.username}",
            },
        ],
    }

    assert json.loads(response_service.content) == {
        "subject": service_acct,
        "links": [
            {
                "rel": "https://webfinger.net/rel/profile-page",
                "type": "text/html",
                "href": f"https://{FEDERATEDCODE_DOMAIN}/users/@{service.user.username}",
            },
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": f"https://{FEDERATEDCODE_DOMAIN}/api/v0/users/@{service.user.username}",
            },
        ],
    }

    assert json.loads(response_purl.content) == {
        "subject": package_acct,
        "links": [
            {
                "rel": "https://webfinger.net/rel/profile-page",
                "type": "text/html",
                "href": f"https://{FEDERATEDCODE_DOMAIN}/purls/@{ package.purl }",
            },
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": f"https://{FEDERATEDCODE_DOMAIN}/api/v0/purls/@{ package.purl }",
            },
        ],
    }
