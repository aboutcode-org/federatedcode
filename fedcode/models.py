#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from git import Repo

from fedcode.utils import ap_collection
from fedcode.utils import clone_git_repo
from fedcode.utils import full_reverse
from fedcode.utils import generate_webfinger
from federatedcode.settings import FEDERATED_CODE_DOMAIN
from federatedcode.settings import FEDERATED_CODE_GIT_PATH


class RemoteActor(models.Model):
    url = models.URLField(primary_key=True)
    username = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)


class Actor(models.Model):
    summary = models.CharField(help_text="profile summary", max_length=100)
    public_key = models.TextField(blank=False)
    local = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Reputation(models.Model):
    voter = models.CharField(max_length=100, help_text="security@vcio.com")
    acceptor = models.CharField(max_length=100, help_text="security@nexb.com")
    positive = models.BooleanField(default=True)

    @property
    def to_ap(self):
        return {
            "voter": self.voter,
            "acceptor": self.acceptor,
            "positive": self.positive,
        }

    class Meta:
        unique_together = [["voter", "acceptor"]]


class Service(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    remote_actor = models.OneToOneField(
        RemoteActor, on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return self.user.username if self.user else self.remote_actor.username

    @property
    def absolute_url_ap(self):
        return full_reverse("user-ap-profile", self.user.username)

    @property
    def to_ap(self):
        return {
            "type": "Service",
            "name": self.user.username,
        }


class Note(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
        help_text="The object's unique global identifier",
    )
    acct = models.CharField(max_length=200)
    content = models.TextField()
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
        help_text="",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="A field to track when notes are created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="A field to track when notes are updated"
    )

    reputation = models.ManyToManyField(
        Reputation,
        blank=True,
        help_text="",
    )

    class Meta:
        ordering = ["-updated_at"]

    @property
    def username(self):
        return self.acct.split("@")[0]

    @property
    def reputation_value(self):
        return (
                self.reputation.filter(positive=True).count()
                - self.reputation.filter(positive=False).count()
        )

    @property
    def absolute_url(self):
        return full_reverse("note-page", self.id)

    @property
    def to_ap(self):
        return {
            "id": self.absolute_url,
            "type": "Note",
            "author": self.acct,
            "content": self.content,
        }


class Purl(Actor):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="The object's unique global identifier",
    )
    remote_actor = models.OneToOneField(
        RemoteActor, on_delete=models.CASCADE, null=True, blank=True
    )
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE)
    string = models.CharField(
        max_length=300, help_text="PURL (no version) ex: @pkg:maven/org.apache.logging", unique=True,
    )
    notes = models.ManyToManyField(Note, blank=True, help_text="""the notes that this purl created ex:
                                                               purl: pkg:.../.../
                                                               affected_by_vulnerabilities: []
                                                               fixing_vulnerabilities: []
                                                               """)

    @property
    def acct(self):
        return generate_webfinger(self.string)

    def __str__(self):
        return self.string

    @property
    def followers_count(self):
        return Follow.objects.filter(purl=self).count()

    @property
    def followers(self):
        return Follow.objects.filter(purl=self).values("person_id")

    @property
    def followers_inboxes(self):
        """Return a followers inbox list"""
        # TODO Try to avoid for loop
        inboxes = []
        for person in self.followers:
            person_inbox = Person.objects.get(id=person["person_id"]).inbox_url
            inboxes.append(person_inbox)
        return inboxes

    # TODO raise error if the purl have a version or qualifiers or subpath
    # def save(self, *args, **kwargs):
    #     if not check_purl_actor(self.string):
    #         return ValidationError(self.string)
    #     super(Purl, self).save(*args, **kwargs)

    @property
    def absolute_url_ap(self):
        return full_reverse("purl-ap-profile", self.string)

    @property
    def inbox_url(self):
        return full_reverse("purl-inbox", self.string)

    @property
    def outbox_url(self):
        return full_reverse("purl-outbox", self.string)

    @property
    def followers_url(self):
        return full_reverse("purl-followers", self.string)

    @property
    def key_id(self):
        return full_reverse("purl-ap-profile", self.string)

    @property
    def to_ap(self):
        return {
            "id": self.absolute_url_ap,
            "type": "Purl",
            "name": self.service.user.username,
            "inbox": self.inbox_url,
            "outbox": self.outbox_url,
            "followers": self.followers_url,
            "publicKey": {
                "id": self.absolute_url_ap,
                "owner": self.service.absolute_url_ap,
                "publicKeyPem": "-----BEGIN PUBLIC KEY-----...-----END PUBLIC KEY-----",
            },
        }


class Person(Actor):
    avatar = models.ImageField(
        upload_to="uploads/", help_text="", default="favicon-16x16.png", null=True
    )
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    remote_actor = models.OneToOneField(
        RemoteActor, on_delete=models.CASCADE, null=True, blank=True
    )

    notes = models.ManyToManyField(Note, blank=True, help_text="")

    @property
    def avatar_absolute_url(self):
        return f'{"https://"}{FEDERATED_CODE_DOMAIN}{self.avatar.url}'

    # TODO raise error if the user doesn't have a user or remote actor
    @property
    def reputation_value(self):
        """if someone like your ( review or note ) you will get +1, dislike: -1"""
        user_reputation = Reputation.objects.filter(acceptor=self.acct)
        return (
                user_reputation.filter(positive=True).count()
                - user_reputation.filter(positive=False).count()
        )

    @property
    def acct(self):
        return generate_webfinger(self.user.username)

    @property
    def url(self):
        return full_reverse("user-profile", self.user.username)

    @property
    def absolute_url_ap(self):
        return full_reverse("user-ap-profile", self.user.username)

    @property
    def inbox_url(self):
        return full_reverse("user-inbox", self.user.username)

    @property
    def outbox_url(self):
        return full_reverse("user-outbox", self.user.username)

    @property
    def following_url(self):
        return full_reverse("user-following", self.user.username)

    @property
    def key_id(self):
        if self.user:
            return full_reverse("user-ap-profile", self.user.username) + "#main-key"
        else:
            return self.remote_actor.url + "#main-key"

    @property
    def to_ap(self):
        return {
            "id": self.absolute_url_ap,
            "type": "Person",
            "name": self.user.username,
            "summary": self.summary,
            "inbox": self.inbox_url,
            "outbox": self.outbox_url,
            "following": self.following_url,
            "image": self.avatar_absolute_url,
            "publicKey": {
                "id": self.absolute_url_ap,
                "owner": self.absolute_url_ap,
                "publicKeyPem": "-----BEGIN PUBLIC KEY-----...-----END PUBLIC KEY-----",
            },
        }


class Follow(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, help_text="")
    purl = models.ForeignKey(Purl, on_delete=models.CASCADE, help_text="")

    created_at = models.DateTimeField(auto_now_add=True, help_text="")
    updated_at = models.DateTimeField(auto_now=True, help_text="")

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.person.user.username} - {self.purl.string}"


class Repository(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
        help_text="The object's unique global identifier",
    )
    name = models.CharField(max_length=50, help_text="repository name")
    url = models.URLField(help_text="Repository url ex: https://github.com/nexB/vulnerablecode-data")
    path = models.CharField(max_length=200, help_text="path of the repository")
    admin = models.ForeignKey(Service, on_delete=models.CASCADE, help_text="admin user ex: VCIO user")
    remote_url = models.CharField(max_length=300, blank=True, null=True, help_text="the url of the repository"
                                                                                   " if this repository is remote")
    last_imported_commit = models.CharField(max_length=64, blank=True, null=True)

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="A field to track when repository are created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="A field to track when repository are updated"
    )

    def __str__(self):
        return self.name

    @property
    def review_count(self):
        return Review.objects.filter(vulnerability__repo=self).count()

    @property
    def git_repo_obj(self):
        return Repo(self.path)

    class Meta:
        unique_together = [["admin", "name"]]
        ordering = ["-updated_at"]

    @property
    def absolute_url(self):
        return full_reverse("repository-page", self.id)

    @property
    def to_ap(self):
        return {
            "id": self.absolute_url,
            "type": "Repository",
            "url": self.url,
        }


class Vulnerability(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
        help_text="The object's unique global identifier",
    )
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255, help_text="ex: VCID-1a68-fd5t-aaam")
    remote_url = models.CharField(max_length=300, blank=True, null=True, help_text="")

    class Meta:
        unique_together = [["repo", "filename"]]

    @property
    def absolute_url(self):
        return full_reverse("vulnerability-page", self.id)

    def __str__(self):
        return self.filename

    @property
    def to_ap(self):
        return {
            "id": self.absolute_url,
            "type": "Vulnerability",
            "repository": self.repo.absolute_url,
            "filename": self.filename,
        }


class Review(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
        help_text="The object's unique global identifier",
    )
    headline = models.CharField(max_length=300, help_text="the review title")
    author = models.ForeignKey(Person, on_delete=models.CASCADE)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)
    filepath = models.CharField(max_length=300, help_text="the review path ex: /apache/httpd/VCID-1a68-fd5t-aaam.yml")
    commit = models.CharField(max_length=300, help_text="ex: 104ccd6a7a41329b2953c96e52792a3d6a9ad8e5")
    data = models.TextField(help_text="review data ex: vulnerability file")
    notes = models.ManyToManyField(Note, blank=True, help_text="")
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="A field to track when review are created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="A field to track when review are updated"
    )
    remote_url = models.CharField(max_length=300, blank=True, null=True, help_text="the review remote url if "
                                                                                   "Remote Review exists")

    class ReviewStatus(models.IntegerChoices):
        OPEN = 0
        DRAFT = 1
        CLOSED = 2
        MERGED = 3

    status = models.SmallIntegerField(
        choices=ReviewStatus.choices,
        null=False,
        blank=False,
        default=0,
        help_text="status of review",
    )

    reputation = models.ManyToManyField(
        Reputation,
        blank=True,
        help_text="",
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.headline}"

    @property
    def reputation_value(self):
        return (
                self.reputation.filter(positive=True).count()
                - self.reputation.filter(positive=False).count()
        )

    @property
    def absolute_url(self):
        return full_reverse("review-page", self.id)

    @property
    def to_ap(self):
        return {
            "id": self.absolute_url,
            "type": "Review",
            "author": self.author.absolute_url_ap,
            "headline": self.headline,
            "repository": str(self.repository.id),
            "filepath": self.filepath,
            "commit": self.commit,
            "content": self.data,
            "comments": ap_collection(self.notes),
            "published": self.created_at,
            "updated": self.updated_at,
        }


class FederateRequest(models.Model):
    target = models.URLField(help_text="The request target ex: (inbox of the targeted actor", blank=False, null=False)
    body = models.TextField(help_text="The request body", blank=False, null=False)
    key_id = models.URLField(help_text="The key url of the actor ex: https://my-example.com/actor#main-key",
                             blank=False, null=False)
    error_message = models.TextField()
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="A field to track when review are created"
    )
    done = models.BooleanField(default=False)


class SyncRequest(models.Model):
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE,
                             help_text="The Git repository where the importer will run"
                             )
    error_message = models.TextField()
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="A field to track when review are created"
    )
    done = models.BooleanField(default=False)


@receiver(post_save, sender=Repository)
def create_git_repo(sender, instance, created, **kwargs):
    if created:
        clone_git_repo(FEDERATED_CODE_GIT_PATH, instance.name, instance.url)
