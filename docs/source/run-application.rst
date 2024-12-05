.. _run-application:

How to Run the Application
===========================

This section provides an example of how to run the Federated Code application.


Step 1: Create a Superuser
---------------------------
Run the following command to create a superuser:

.. code-block:: bash

    python manage.py createsuperuser


Step 2: Create a Service Account
---------------------------------
Only superusers can create a Service account (e.g., VCIO or SCIO).

1. Access the Django admin panel.
http://127.0.0.1:8000/admin/

2. Create a new user through the admin interface.
http://127.0.0.1:8000/admin/auth/user/add/

3. Assign the newly created user as a Service account.
http://127.0.0.1:8000/admin/fedcode/service/


Step 3: Service Login and Git Repository Creation
--------------------------------------------------
Now you have a Service login ex `VCIO` use this credential to create a Git Repository
https://github.com/aboutcode-org/vulnerablecode-data

Visit http://127.0.0.1:8000/create-repo

Step 4:
--------
To initiate a sync of the master branch, you can either click on the sync request
button in the app or send an HTTP request directly to the endpoint using the auth service.
The endpoint is: `repository/<uuid:repository_id>/sync-repo/`

Visit http://127.0.0.1:8000/repo-list.


Alternatively, you can integrate this action with GitHub Actions or any other
CI tool to trigger the sync automatically whenever new data is pushed to the
master branch.

Here’s an example of how to send the request manually using curl:
ex:

.. code-block:: bash

  curl -v -X POST \
    -H "Authorization: Token your-auth-token" \
    http://127.0.0.1:8000/repository/<uuid:repository_id>/sync-repo/


**Note:** You can retrieve the service token after authenticating via the endpoint
`api/v0/users/@<str:username>`.

Step 5:
--------
The admin should regularly run the following commands, either manually or in a loop:

.. code-block:: bash

    python manage.py sync && python manage.py federate

Users can now log in or sign up, create and review metadata, and vote for packages.

Happy Federation, everyone!
