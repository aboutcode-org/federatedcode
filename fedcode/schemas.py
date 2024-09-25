#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from typing import List

from ninja import ModelSchema

from fedcode import models


class RemoteActor(ModelSchema):
    class Meta:
        model = models.RemoteActor
        fields = ["url", "username", "created_at", "updated_at"]


class Repository(ModelSchema):
    """
    A git repository used as a backing storage for Package and vulnerability data
    """

    class Meta:
        model = models.Repository
        exclude = ["admin"]


class Vulnerability(ModelSchema):
    repo: Repository

    class Meta:
        model = models.Vulnerability
        fields = "__all__"


class Reputation(ModelSchema):
    """
    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-like
    https://www.w3.org/ns/activitystreams#Dislike
    """

    class Meta:
        model = models.Reputation
        fields = ["object_id", "voter", "positive"]


class Note(ModelSchema):
    """
    A Note is a message send by a Person or Package.
    The content is either a plain text message or structured YAML.
    If the author is a Package actor then the content is always YAML
    If the author is a Person actor then the content is always plain text
    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-note
    """

    reputation: List[Reputation]
    reply_to: "Note"

    class Meta:
        model = models.Note
        fields = "__all__"


Note.model_rebuild()


class Package(ModelSchema):
    """
    A software package identified by its package url ( PURL ) ignoring versions
    """

    remote_actor: RemoteActor
    notes: List[Note]

    class Meta:
        model = models.Package
        exclude = ["service"]
