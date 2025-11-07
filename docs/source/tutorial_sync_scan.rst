.. _tutorial_federate_scan:

Syncing ScanCode Metadata with FederatedCode
==============================================

Fork the FederatedCode Data Package Scan Repository
-----------------------------------------------------

Visit https://github.com/aboutcode-org/aboutcode-packages-npm-385 and fork the repository.

Add Data Repository in FederatedCode
-------------------------------------

Go to http://127.0.0.1:8000/create-repo and add the repository URL: https://github.com/<YOUR-USER-NAME>/aboutcode-packages-npm-385, and click Submit.

.. image:: img/tutorial_getting_started_repo_add.jpg

Sync Package Scan
-----------------

Run the following command to sync the scan metadata from the FederatedCode Git repository

.. code-block:: bash

    python manage.py sync sync_scancode_scans


Click on `Packages` link
--------------------------

.. image:: img/tutorial_getting_started_step_packages.jpg

Click on any PURL link
----------------------

.. image:: img/tutorial_getting_started_step_package_list.jpg

Package Activity
----------------

.. image:: img/tutorial_getting_started_step_package_activity.jpg

