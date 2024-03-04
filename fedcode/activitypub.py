#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import json
import logging
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Literal
from typing import Optional
from urllib.parse import urlparse

from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.urls import resolve

from federatedcode.settings import FEDERATED_CODE_DOMAIN
from federatedcode.settings import FEDERATED_CODE_GIT_PATH

from .models import Follow, FederateRequest
from .models import Note
from .models import Person
from .models import Package
from .models import RemoteActor
from .models import Repository
from .models import Review
from .models import Service
from .models import Vulnerability
from .utils import fetch_actor
from .utils import full_resolve
from .utils import full_reverse
from .utils import webfinger_actor

CONTENT_TYPE = "application/activity+json"
ACTOR_TYPES = ["Person", "Package"]

ACTOR_PAGES = {"purl-profile": Package, "user-profile": Person}

ACTIVITY_TYPES = ["Follow", "UnFollow", "Create", "Update", "Delete", "Sync"]

OBJECT_TYPES = {
    "Note": Note,
    "Review": Review,
    "Repository": Repository,
    "Vulnerability": Vulnerability,
}

AP_VALID_HEADERS = [
    'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    "application/activity+json",
]

AP_CONTEXT = {
    "@context": ["https://www.w3.org/ns/activitystreams", "..........."],
}

AP_TARGET = {"cc": "https://www.w3.org/ns/activitystreams#Public"}

OBJ_PAGE = {
    "Note": "note-page",
    "Review": "review-page",
    "Repository": "repository-page",
    "Vulnerability": "vulnerability-page",
}

URL_MAPPER = {
    "user-ap-profile": "username",
    "purl-ap-profile": "purl_string",
    "review-page": "uuid",
    "repository-page": "uuid",
    "note-page": "uuid",
    "vulnerability-page": "str",
}

logger = logging.getLogger(__name__)


def check_and_r_ap_context(request):
    """
    check activitypub context request and return request without @context
    """
    if request.get("@context") == AP_CONTEXT["@context"]:
        request.pop("@context")
        return request
    else:
        return None


def add_ap_target(response):
    """
    Add target activitypub response
    """
    if response is not dict:
        raise KeyError("Invalid response")

    if not response.get("cc"):
        response.append(**AP_TARGET)

    return response


def has_valid_header(view):
    """
    check if the request header in the AP_VALID_HEADERS if yes return view else return HttpResponseForbidden
    """

    def wrapper(request, *args, **kwargs):
        content_type = request.headers.get("Content-Type")
        if content_type in AP_VALID_HEADERS:
            return view(request, *args, **kwargs)
        else:
            return

    return wrapper


@dataclass
class Activity:
    type: Literal["Follow", "UnFollow", "Create", "Update", "Delete", "Sync"]
    actor: Optional[str | dict]
    object: Optional[str | dict]
    to: list = field(default_factory=list)
    id: str = None

    def handler(self):
        ap_actor = ApActor(**self.actor) if isinstance(self.actor, dict) else ApActor(id=self.actor)
        ap_object = (
            ApObject(**self.object) if isinstance(self.object, dict) else ApObject(id=self.object)
        )
        return ACTIVITY_MAPPER[self.type](actor=ap_actor, object=ap_object, to=self.to).save()

    @classmethod
    def federate(cls, targets, body, key_id):
        """
        Send the signed request body and key_id to the targets list of domains
        """
        for target in targets:
            target_domain = urlparse(target).netloc
            if target_domain != FEDERATED_CODE_DOMAIN:  # TODO Add a server whitelist if necessary
                try:
                    FederateRequest.objects.create(target=target, body=body, key_id=key_id)
                except Exception as e:
                    logger.error(f"{e}")


@dataclass
class ApActor:
    type: Literal["Person", "Package"] = None
    id: str = None
    name: Optional[str] = None
    purl: Optional[str] = None
    summary: Optional[str] = None
    inbox: str = None
    outbox: str = None
    following: Optional[str] = None
    followers: Optional[str] = None
    image: Optional[str] = None

    def get_by_type(self):
        if self.type in ACTOR_TYPES:
            if self.type == ACTOR_TYPES[0]:
                return Person.objects.get_or_none(user__username=self.name).to_ap()

            elif self.type == ACTOR_TYPES[1]:
                return Package.objects.get_or_none(purl=self.name).to_ap()

    def get(self):
        obj_id, page_name = full_resolve(self.id)
        if page_name == "purl-ap-profile":
            try:
                purl = Package.objects.get(purl=obj_id["purl_string"])
            except Package.DoesNotExist:
                purl = None
            return purl

        elif page_name == "user-ap-profile":
            try:
                user = User.objects.get(username=obj_id["username"])
                if hasattr(user, "person"):
                    return user.person
                elif hasattr(user, "service"):
                    return user.service
            except User.DoesNotExist:
                user = None
        return None


@dataclass
class ApObject:
    type: Literal["Note", "Review", "Repository", "Vulnerability"] = None
    id: str = None
    content: str = None
    reply_to: str = None
    repository: str = None
    branch: str = None
    filename: str = None
    hash: str = None
    headline: str = None
    name: str = None
    url: str = None
    vulnerability: str = None
    published: str = None
    commit: str = None
    filepath: str = None

    def get_object(self):
        if self.id:
            obj_id, page_name = full_resolve(self.id)
            identifier = URL_MAPPER[page_name]
            return OBJECT_TYPES[self.type].objects.get(id=obj_id[identifier])
        raise ValueError("Invalid object id")


@dataclass
class FollowActivity:
    """
    https://www.w3.org/ns/activitystreams#Follow
    """
    type = "Follow"
    actor: ApActor
    object: ApActor
    to: list = field(default_factory=list)

    def save(self):
        # TODO simplify this section
        actor = self.actor.get()
        parser = urlparse(self.actor.id)
        if not actor and parser.netloc != FEDERATED_CODE_DOMAIN:
            # remote person ( send a remote follow request if created and assume the request was accepted )
            resolver = resolve(parser.path)
            identity = URL_MAPPER[resolver.url_name]
            url = webfinger_actor(parser.netloc, resolver.kwargs[identity])
            actor_details = fetch_actor(url)
            remote_actor, created = RemoteActor.objects.get_or_create(
                username=actor_details["name"], url=actor_details["id"]
            )
            actor, created = Person.objects.get_or_create(remote_actor=remote_actor)
            Activity.federate(targets=self.to, body=self.to_ap(), key_id=actor.key_id)
        # --------------------------------------------
        parser = urlparse(self.object.id)
        resolver = resolve(parser.path)
        obj_id, page_name = resolver.kwargs, resolver.url_name
        identity = URL_MAPPER[page_name]
        if parser.netloc == FEDERATED_CODE_DOMAIN:
            # local package
            try:
                package = Package.objects.get(purl=obj_id["purl_string"])
            except Package.DoesNotExist:
                package = None
        else:
            # remote package
            url = webfinger_actor(parser.netloc, resolver.kwargs[identity])
            package_details = fetch_actor(url)
            remote_actor, created = RemoteActor.objects.get_or_create(
                username=package_details["name"], url=package_details["id"]
            )
            package, created = Package.objects.get_or_create(
                remote_actor=remote_actor, purl=package_details["purl"]
            )
            Activity.federate(targets=self.to, body=self.to_ap(), key_id=actor.key_id)

        if package and actor:
            Follow.objects.get_or_create(person=actor, package=package)
            return self.succeeded_ap_rs()

        return self.failed_ap_rs()

    def succeeded_ap_rs(self):
        """Response for successfully deleting the object"""
        return JsonResponse({}, status=201)

    def failed_ap_rs(self):
        """Response for failure deleting the object"""
        return JsonResponse({}, status=405)

    def to_ap(self):
        """Follow activity in activitypub format"""
        return {
            **AP_CONTEXT,
            "type": self.type,
            "actor": asdict(self.actor),
            "object": asdict(self.object),
            "to": self.to,
            **AP_TARGET,
        }


@dataclass
class CreateActivity:
    """
    https://www.w3.org/TR/activitypub/#create-activity-outbox
    """
    type = "Create"
    actor: ApActor
    object: ApObject
    to: list = field(default_factory=list)

    def save(self):
        new_obj, created = None, None
        actor = self.actor.get()
        if not actor:
            return self.failed_ap_rs()

        if isinstance(actor, Person):
            if self.object.type == "Note":
                reply_to = None
                if self.object.reply_to:
                    note_id = full_resolve(self.object.reply_to)
                    reply_to = Note.objects.get_or_none(id=note_id)

                new_obj, created = Note.objects.get_or_create(
                    acct=actor.acct,
                    content=self.object.content,
                    reply_to=reply_to,
                )
            elif self.object.type == "Review" and self.object.repository:
                obj_id, page_name = full_resolve(self.object.repository)
                repo = Repository.objects.get(id=obj_id["repository_id"])

                new_obj, created = Review.objects.get_or_create(
                    headline=self.object.headline,
                    author=actor,
                    filepath=self.object.filepath,
                    repository=repo,
                    data=self.object.content,
                    commit=self.object.commit,
                    status=0,  # OPEN
                )
            Activity.federate(targets=self.to, body=self.to_ap(), key_id=actor.key_id)
        elif isinstance(actor, Package):
            if self.object.type == "Note":
                reply_to = None
                if self.object.reply_to:
                    note_id = self.object.reply_to
                    reply_to = Note.objects.get_or_none(id=note_id)

                new_obj, created = Note.objects.get_or_create(
                    acct=actor.acct,
                    content=self.object.content,
                    reply_to=reply_to,
                )
            Activity.federate(targets=self.to, body=self.to_ap(), key_id=actor.key_id)
        elif isinstance(actor, Service):
            if self.object.type == "Repository":
                new_obj, created = Repository.objects.get_or_create(
                    url=self.object.url,
                    path=FEDERATED_CODE_GIT_PATH,
                    admin=actor,
                )

        return self.succeeded_ap_rs(new_obj) if created else self.failed_ap_rs()

    def succeeded_ap_rs(self, new_obj):
        """Response for successfully deleting the object"""
        return JsonResponse(
            {"Location": full_reverse(OBJ_PAGE[self.object.type], new_obj.id)},
            status=201,
        )

    def failed_ap_rs(self):
        """Response for failure deleting the object"""
        return HttpResponseBadRequest("Invalid Create Activity request")

    def to_ap(self):
        """Request for creating object in activitypub format"""
        return {
            **AP_CONTEXT,
            "type": self.type,
            "actor": self.actor if isinstance(self.actor, dict) else asdict(self.actor),
            "object": self.object if isinstance(self.actor, dict) else asdict(self.object),
            "to": self.to,
            **AP_TARGET,
        }


@dataclass
class UpdateActivity:
    """
    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-update
    """
    type = "Update"
    actor: ApActor
    object: ApObject
    to: list = field(default_factory=list)

    def save(self):
        updated_obj = None
        actor = self.actor.get()
        old_obj = self.object.get_object()
        if not actor:
            return self.failed_ap_rs()

        updated_param = {
            "Note": {"content": self.object.content},
            "Review": {"headline": self.object.headline, "data": self.object.content},
            "Repository": {"url": self.object.url},
        }

        if (
                (isinstance(actor, Person) and self.object.type in ["Note", "Review"])
                or (isinstance(actor, Service) and self.object.type == "Repository")
                or (isinstance(actor, Package) and self.object.type == "Note")
        ):
            for key, value in updated_param[self.object.type].items():
                if value:
                    setattr(old_obj, key, value)
            old_obj.save()

        Activity.federate(targets=self.to, body=self.to_ap(), key_id=actor.key_id)
        return self.succeeded_ap_rs(old_obj.to_ap)

    def succeeded_ap_rs(self, update_obj):
        """Response for successfully deleting the object"""
        return JsonResponse(update_obj, status=200)

    def failed_ap_rs(self):
        """Response for failure deleting the object"""
        return HttpResponseBadRequest("Method Not Allowed", status=405)

    def to_ap(self):
        """Request for updating object in activitypub format"""
        return {
            **AP_CONTEXT,
            "type": self.type,
            "actor": asdict(self.actor),
            "object": asdict(self.object),
            "to": self.object,
            **AP_TARGET,
        }


@dataclass
class DeleteActivity:
    """
    https://www.w3.org/ns/activitystreams#Delete
    """
    actor: ApActor
    object: ApObject
    type = "Delete"
    to: list = field(default_factory=list)

    def save(self):
        actor = self.actor.get()
        if not actor:
            return self.failed_ap_rs()

        if (
                (type(actor) is Person and self.object.type in ["Note", "Review"])
                or (type(actor) is Package and self.object.type in ["Note"])
                or (type(actor) is Service and self.object.type == ["Repository", "Package"])
        ):
            instance = self.object.get_object()
            instance.delete()
            Activity.federate(targets=self.to, body=self.to_ap(), key_id=actor.key_id)
            return self.succeeded_ap_rs()
        else:
            return self.failed_ap_rs()

    def ap_rq(self):
        """Request for deleting object in activitypub format"""
        return {**AP_CONTEXT, "type": self.type, "actor": self.actor, "to": self.object}

    def succeeded_ap_rs(self):
        """Response for successfully deleting the object"""
        return JsonResponse({"message": "The object has been deleted successfully"}, status=200)

    def failed_ap_rs(self):
        """Response for failure deleting the object"""
        return JsonResponse("Invalid object", status=404)

    def to_ap(self):
        return {
            **AP_CONTEXT,
            "type": self.type,
            "actor": asdict(self.actor),
            "object": asdict(self.object),
            "to": self.object,
            **AP_TARGET,
        }


def create_activity_obj(data):
    """Convert json object to activity object"""
    payload = json.loads(data)
    payload_without_context = check_and_r_ap_context(payload)
    return Activity(**payload_without_context)


@dataclass
class UnFollowActivity:
    """

    """
    type = "UnFollow"
    actor: ApActor
    object: ApActor
    to: list = field(default_factory=list)

    def save(self):
        actor = self.actor.get()
        if not type(actor) is Person:
            return self.failed_ap_rs()
        else:
            obj_id, page_name = full_resolve(self.object.id)
            package = Package.objects.get(purl=obj_id["purl_string"])
            follow_obj = Follow.objects.get(person_id=actor.id, package=package)
            follow_obj.delete()
            return self.succeeded_ap_rs()

    def succeeded_ap_rs(self):
        """Response for successfully deleting the object"""
        return JsonResponse({"Location": ""}, status=201)

    def failed_ap_rs(self):
        """Response for failure deleting the object"""
        return JsonResponse({}, status=405)

    def to_ap(self):
        """Follow activity in activitypub format"""
        return {
            **AP_CONTEXT,
            "type": self.type,
            "actor": asdict(self.actor),
            "object": asdict(self.object),
            "to": self.object,
            **AP_TARGET,
        }


@dataclass
class SyncActivity:
    """
    The Sync activity is a custom activity where a Service user
    can send a request to run the Importer and receive
    all the followed Package data
    """
    type = "Sync"
    actor: ApActor
    object: ApObject
    to: list = field(default_factory=list)

    def save(self):
        actor = self.actor.get()
        if not actor:
            return self.failed_ap_rs()
        repo = self.object.get_object().git_repo_obj
        repo.remotes.origin.pull()
        return self.succeeded_ap_rs()

    def succeeded_ap_rs(self):
        """Response for successfully deleting the object"""
        return JsonResponse({}, status=201)

    def failed_ap_rs(self):
        """Response for failure deleting the object"""
        return JsonResponse({}, status=405)


ACTIVITY_MAPPER = {
    "Create": CreateActivity,
    "Update": UpdateActivity,
    "Delete": DeleteActivity,
    "Follow": FollowActivity,
    "UnFollow": UnFollowActivity,
    "Sync": SyncActivity,
}
