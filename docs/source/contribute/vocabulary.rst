.. _vocabulary:

FederatedCode Vocabulary
=========================
FederatedCode Vocabulary’s intended to be an extension of
`Activity Vocabulary <https://www.w3.org/TR/activitystreams-vocabulary/>`__.

Actors
*******

Package
-------
  .. code-block:: JSON

    {
        "@context": ["https://www.w3.org/ns/activitystreams", "....."],
        "type": "Package",
        "name": "vcio",
        "followers": "https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/followers/",
        "id": "https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
        "inbox": "https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/inbox",
        "outbox": "https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/outbox",
        "publicKey": {
            "id": "https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
            "owner": "https://127.0.0.1:8000/api/v0/users/@ziad",
            "publicKeyPem": "-----BEGIN PUBLIC KEY-----...-----END PUBLIC " "KEY-----",
        }
    }

Person
-------
.. code-block:: JSON

    {
        "@context": ["https://www.w3.org/ns/activitystreams", "....."],
        "type": "Person",
        "summary": "Hello This is my profile",
        "following": "https://127.0.0.1:8000/api/v0/users/@ziad/following/",
        "id": "https://127.0.0.1:8000/api/v0/users/@ziad",
        "image": "https://127.0.0.1:8000/media/favicon-16x16.png",
        "inbox": "https://127.0.0.1:8000/api/v0/users/@ziad/inbox",
        "name": "ziad",
        "outbox": "https://127.0.0.1:8000/api/v0/users/@ziad/outbox",
        "publicKey": {
            "id": "https://127.0.0.1:8000/api/v0/users/@ziad",
            "owner": "https://127.0.0.1:8000/api/v0/users/@ziad",
            "publicKeyPem": "-----BEGIN PUBLIC KEY-----...-----END PUBLIC " "KEY-----",
        }
    }

Service
-------
.. code-block:: JSON

    {
        "@context": ["https://www.w3.org/ns/activitystreams", "....."],
        "type": "Service",
        "name": "vcio"
    }

Activity
********

Follow
-------
  .. code-block:: JSON

    {
        "@context": ["https://www.w3.org/ns/activitystreams", "....."],
        "type": "Follow",
        "actor": "https://127.0.0.1:8000/api/v0/users/@ziad",
        "object": {
            "id": "https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
            "type": "Purl"
        },
    }

Create
-------
  .. code-block:: JSON

        {
            "@context": ["https://www.w3.org/ns/activitystreams", "....."],
            "type": "Create",
            "actor": "https://127.0.0.1:8000/api/v0/users/@vcio",
            "object": {
                "type": "Repository",
                "name": "vulnerablecode",
                "url": "https://github.com/nexB/vulnerablecode-data",
            },
        }

Update
-------
  .. code-block:: JSON

        {
            "@context": ["https://www.w3.org/ns/activitystreams", "....."],
            "type": "Update",
            "actor": "https://127.0.0.1:8000/api/v0/users/@ziad",
            "object": {
                "id": "https://127.0.0.1:8000/notes/3701d4b6-a7cf-41ee-9144-35f9d70afe0b",
                "type": "Note",
                "content": "Hello World!",
            },
        }

Delete
-------
  .. code-block:: JSON

    {
        "@context": ["https://www.w3.org/ns/activitystreams", "....."],
        "type": "Delete",
        "actor": "https://127.0.0.1:8000/api/v0/users/@ziad",
        "object": {
            "type": "Note",
            "id": "https://127.0.0.1:8000/notes/3701d4b6-a7cf-41ee-9144-35f9d70afe0b",
        },
    }


UnFollow
--------
  .. code-block:: JSON

    {
        "@context": ["https://www.w3.org/ns/activitystreams", "....."],
        "type": "UnFollow",
        "actor": "https://127.0.0.1:8000/api/v0/users/@ziad",
        "object": {
            "type": "Purl",
            "id": "https://127.0.0.1:8000/api/v0/purls/@pkg:maven/org.apache.logging/",
        },
    }

Sync
-----
  .. code-block:: JSON

        {
            "@context": ["https://www.w3.org/ns/activitystreams", "....."],
            "type": "Sync",
            "actor": "https://127.0.0.1:8000/users/@vcio",
            "object": {
                "type": "Repository",
                "id": "https://127.0.0.1:8000/repository/3701d4b6-a7cf-41ee-9144-35f9d70afe0b/",
            },
        }

Objects
********

Note
-----

  .. code-block:: JSON

      {
        "type": "Note",
        "id": "https://127.0.0.1:8000/notes/3701d4b6-a7cf-41ee-9144-35f9d70afe0b",
        "author": "pkg:maven/org.apache.logging@127.0.0.1:8000",
        "content": "purl: pkg:maven/org.apache.logging@2.23-r0?arch=aarch64&distroversion=edge&reponame=community
            affected_by_vulnerabilities: []
            fixing_vulnerabilities: []",
        "mediaType": "application/yaml"
        }

OR Note
--------

  .. code-block:: JSON

    {
        "type": "Note",
        "id": "https://127.0.0.1:8000/notes/3701d4b6-a7cf-41ee-9144-35f9d70afe0b",
        "author": "ziad@vcio",
        "content": "I think this review ",
        "mediaType": "text/plain"
        "reply_to": "https://127.0.0.1:8000/notes/de5a3ab3-9ec7-4943-8061-cbe4b8f01942",
    }


Review
-------
  .. code-block:: JSON

    {
        "id": "https://127.0.0.1:8000/reviews/3701d4b6-a7cf-41ee-9144-35f9d70afe0b/",
        "type": "Review",
        "author": "https://127.0.0.1:8000/api/v0/users/@ziad",
        "headline": "Missing data at ( VCIO-xx-xx-xx )",
        "filepath": "/apache/httpd/VCID-1a68-fd5t-aaam.yml",
        "repository": "https://127.0.0.1:8000/repository/3701d4b6-a7cf-41ee-9144-35f9d70afe0b/",
        "content": "diff text",
        "commit": "104ccd6a7a41329b2953c96e52792a3d6a9ad8e5",
        "comments": {
            "type": "OrderedCollection",
            "totalItems": 1,
            "orderedItems": [
                    {       "type": "Note",
                            "id": "https://127.0.0.1:8000/notes/3701d4b6-a7cf-41ee-9144-35f9d70afe0b",
                            "author": "https://127.0.0.1:8000/api/v0/users/@ziad",
                            "content": "The affected_by_vulnerabilities should be [ ... ] ",
                    }
            ],
        },
        "published": "2015-02-10T15:04:55Z",
        "updated": "2015-02-10T15:04:55Z",
    }

Repository
------------
  .. code-block:: JSON

    {
        "id": "https://127.0.0.1:8000/repository/dfc1f9bf-3f23-484b-9187-4c9bc89d7cbb/",
        "type": "Repository",
        "url": "https://github.com/nexB/fake-repo"
    }

Vulnerability
---------------
  .. code-block:: JSON

    {
        "id": "https://127.0.0.1:8000/vulnerability/VCID-1155-4sem-aaaq/",
        "type": "Vulnerability",
        "repository": "https://127.0.0.1:8000/repository/dfc1f9bf-3f23-484b-9187-4c9bc89d7cbb/",
    }


Like
------
  .. code-block:: JSON

    {
      "type": "Like",
      "actor": "ziad@vcio",
      "object": {
        "type": "Note",
        "content": "A simple note"
      }
    }

Dislike
--------
  .. code-block:: JSON

    {
      "type": "Dislike",
      "actor": "ziad@vcio",
      "object": {
        "type": "Note",
        "content": "A simple note"
      }
    }
