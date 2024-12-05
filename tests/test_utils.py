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

from fedcode.activitypub import AP_CONTEXT
from fedcode.activitypub import Activity
from fedcode.activitypub import create_activity_obj
from fedcode.utils import check_purl_actor
from fedcode.utils import full_resolve
from fedcode.utils import full_reverse


@pytest.mark.parametrize(
    "payload,expected",
    [
        (
            {
                **AP_CONTEXT,
                "type": "Create",
                "actor": "https://dustycloud.org/chris/",
                "object": "https://rhiaro.co.uk/2016/05/minimal-activitypub",
            },
            Activity(
                type="Create",
                actor="https://dustycloud.org/chris/",
                object="https://rhiaro.co.uk/2016/05/minimal-activitypub",
            ),
        ),
        (
            {
                **AP_CONTEXT,
                "id": "https://example.com/api/activity/2",
                "type": "Update",
                "actor": "https://example.com/chris/",
                "object": {
                    "type": "Note",
                    "id": "https://example.com/note/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
                    "actor": "https://example.com/user/@user1",
                    "content": "we should fix purl",
                },
            },
            Activity(
                id="https://example.com/api/activity/2",
                type="Update",
                actor="https://example.com/chris/",
                object={
                    "type": "Note",
                    "id": "https://example.com/note/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
                    "actor": "https://example.com/user/@user1",
                    "content": "we should fix purl",
                },
            ),
        ),
    ],
)
def test_load_activity(payload, expected):
    json_payload = json.dumps(payload)
    assert create_activity_obj(json_payload) == expected


def test_full_reverse():
    assert (
        full_reverse("note-page", "7e676ad1-995d-405c-a829-cb39813c74e5")
        == "https://127.0.0.1:8000/notes/7e676ad1-995d-405c-a829-cb39813c74e5"
    )


def test_full_resolve():
    result_args, result_url_name = full_resolve(
        f"https://127.0.0.1:8000/notes/7e676ad1-995d-405c-a829-cb39813c74e5"
    )
    assert "7e676ad1-995d-405c-a829-cb39813c74e5" == str(result_args["uuid"])
    assert "note-page" == result_url_name


def test_check_purl_actor():
    assert check_purl_actor("pkg:maven/org.apache.logging")
