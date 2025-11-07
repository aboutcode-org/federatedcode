.. _tutorial_getting_started:

Getting Started
===============

In this tutorial, we will guide you through the step-by-step process of getting started with syncing
and federating package metadata and vulnerability metadata.

.. note::
    This tutorial assumes that you have a working installation of FederatedCode.
    If you don't, please refer to the :ref:`installation` page.

Create Admin User
-------------------

.. code-block:: bash

    python manage.py createsuperuser

Log in to FederatedCode Admin
------------------------------

Navigate to http://127.0.0.1:8000/admin/ and log in using the credentials created in the previous step.

.. image:: img/tutorial_getting_started_admin.jpg

Create Service User
--------------------
1. Go to http://127.0.0.1:8000/admin/fedcode/service/add/ and create a service.

2. Select the newly created superuser as the user, and leave the "remote-actor" field empty.

.. image:: img/tutorial_getting_started_service_creation.jpg

.. note::
    Or sign up and ask the FederatedCode admin to promote your account
    to a service account.

    .. image:: img/tutorial_getting_started_user_creation.png


