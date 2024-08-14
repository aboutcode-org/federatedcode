import pytest
from django.contrib.auth.models import User
from fedcode_test_utils import mute_post_save_signal  # NOQA

from fedcode.models import Note
from fedcode.models import Package
from fedcode.models import Person
from fedcode.models import Repository
from fedcode.models import Reputation
from fedcode.models import Review
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
def package(db, service):
    return Package.objects.create(
        purl="pkg:maven/org.apache.logging",
        service=service,
    )


@pytest.fixture
def person(db):
    user1 = User.objects.create(
        username="ziad",
        email="ziad@nexb.com",
        password="complex-password",
    )
    return Person.objects.create(user=user1, summary="Hello World", public_key="PUBLIC_KEY")


@pytest.mark.django_db
def test_actors_to_ap(person, package, service):
    assert person.to_ap == {
        "id": "https://127.0.0.1:8000/api/v0/users/@ziad",
        "type": "Person",
        "name": "ziad",
        "summary": "Hello World",
        "following": "https://127.0.0.1:8000/api/v0/users/@ziad/following/",
        "image": "https://127.0.0.1:8000/media/favicon-16x16.png",
        "inbox": "https://127.0.0.1:8000/api/v0/users/@ziad/inbox",
        "outbox": "https://127.0.0.1:8000/api/v0/users/@ziad/outbox",
        "publicKey": {
            "id": "https://127.0.0.1:8000/api/v0/users/@ziad",
            "owner": "https://127.0.0.1:8000/api/v0/users/@ziad",
            "publicKeyPem": "-----BEGIN PUBLIC KEY-----...-----END PUBLIC KEY-----",
        },
    }
    assert package.to_ap == {
        "id": f"https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
        "type": "Package",
        "purl": "pkg:maven/org.apache.logging",
        "name": "vcio",
        "followers": f"https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/followers/",
        "inbox": f"https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/inbox",
        "outbox": f"https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/outbox",
        "publicKey": {
            "id": "https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
            "owner": "https://127.0.0.1:8000/api/v0/users/@vcio",
            "publicKeyPem": "-----BEGIN PUBLIC KEY-----...-----END PUBLIC KEY-----",
        },
    }
    assert service.to_ap == {
        "type": "Service",
        "name": "vcio",
    }


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
    return Vulnerability.objects.create(
        id="VCID-1155-4sem-aaaq",
        repo=repo,
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


@pytest.fixture
def note(db):
    return Note.objects.create(
        acct="ziad@127.0.0.1:8000",
        content="Comment #1",
    )


@pytest.fixture
def rep(db, note):
    return Reputation.objects.create(
        voter="ziad@vcio",
        positive=True,
        content_object=note,
    )


@pytest.mark.django_db
def test_objects_to_ap(repo, review, vulnerability, note, rep, mute_post_save_signal):
    assert repo.to_ap == {
        "id": f"https://127.0.0.1:8000/repository/{repo.id}/",
        "type": "Repository",
        "url": "https://github.com/nexB/fake-repo",
    }

    assert review.to_ap == {
        "id": f"https://127.0.0.1:8000/reviews/{review.id}/",
        "type": "Review",
        "headline": review.headline,
        "content": review.data,
        "author": f"https://127.0.0.1:8000/api/v0/users/@{review.author.user.username}",
        "comments": {"orderedItems": [], "totalItems": 0, "type": "OrderedCollection"},
        "commit": review.commit,
        "published": review.created_at,
        "updated": review.updated_at,
        "repository": str(repo.id),
        "filepath": review.filepath,
    }
    assert vulnerability.to_ap == {
        "id": f"https://127.0.0.1:8000/vulnerability/{vulnerability.id}/",
        "type": "Vulnerability",
        "repository": f"https://127.0.0.1:8000/repository/{vulnerability.repo.id}/",
    }

    assert note.to_ap == {
        "type": "Note",
        "id": f"https://127.0.0.1:8000/notes/{note.id}",
        "author": note.acct,
        "content": note.content,
    }

    assert rep.to_ap == {
        "type": "Like",
        "actor": "ziad@vcio",
        "object": {
            "type": "Note",
            "id": f"https://127.0.0.1:8000/notes/{note.id}",
            "author": note.acct,
            "content": note.content,
        },
    }
