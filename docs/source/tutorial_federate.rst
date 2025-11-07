Federating Package Activity and Repository Sync
===============================================

Federating Package Activity
----------------------------

Run the following command to send activity updates to existing subscribers of the package

.. code-block:: bash

    python manage.py federate

Notifying FederatedCode of Repository Changes
----------------------------------------------

To create a sync request to a FederatedCode instance

you can send an HTTP POST request directly to this endpoint:
`repository/<uuid:repository_id>/sync-repo/`

Example:
http://127.0.0.1:8000/repository/3g8d-4e5d-abff-90865d1e13b1/sync-repo/

**Note:** You can find the repository ID by visiting http://127.0.0.1:8000/repo-list.

Here’s an example of how to send the request manually using `curl`:

.. code-block:: bash

  curl -v -X POST \
    -H "Authorization: Token your-auth-token" \
    http://127.0.0.1:8000/repository/<uuid:repository_id>/sync-repo/

**Note:** You can retrieve the service token after authenticating via this endpoint:
`api/v0/auth/token/`

.. note::
    You can also integrate this action with GitHub Actions
    or any other CI tool to automatically trigger
    the sync request whenever new data is pushed to the main branch.


