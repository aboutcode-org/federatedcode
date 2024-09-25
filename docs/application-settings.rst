.. _federatedcode_settings:

Application Settings
====================

FederatedCode is configured with environment variables stored in a ``.env`` file.
Use the ``docker.env`` file if your run with containers and docker.

The ``.env`` file is created at the root of the FederatedCode codebase during its
installation. You can configure your preferences using the following settings in the ``.env``
file.

.. note::
    FederatedCode is based on the Django web framework and its settings system.
    The list of settings available in Django is documented at
    `Django Settings <https://docs.djangoproject.com/en/dev/ref/settings/>`_.

.. tip::
    Settings specific to FederatedCode are all prefixed with ``FEDERATEDCODE_``.

DATABASE
--------

The database can be configured using the following settings (we list the defaults here)::

    FEDERATEDCODE_DB_ENGINE=django.db.backends.postgresql
    FEDERATEDCODE_DB_HOST=localhost
    FEDERATEDCODE_DB_NAME=federatedcode
    FEDERATEDCODE_DB_USER=federatedcode
    FEDERATEDCODE_DB_PASSWORD=federatedcode
    FEDERATEDCODE_DB_PORT=5432

.. _federatedcode_settings_require_authentication:

FEDERATEDCODE_REQUIRE_AUTHENTICATION
-----------------------------------------

By default, the FederatedCode Web UI and REST API are only available with
authentication.

The authentication system can be disabled with this settings::

    FEDERATEDCODE_REQUIRE_AUTHENTICATION=False

Once disabled, all the Web UI views and REST API endpoints will stop forcing the user
to login to gain access.


See :ref:`rest_api_authentication` for details on using the ``API key``
authentication system in the REST API.

.. _federatedcode_settings_workspace_location:

FEDERATEDCODE_WORKSPACE_LOCATION
-----------------------------------

This setting defines the workspace location of a given instance.
The **workspace** is the directory where **all of the instance's work files are stored**
including the clone of git repositories::

    FEDERATEDCODE_WORKSPACE_LOCATION=/var/federatedcode/workspace/

It defaults to a :guilabel:`var/` directory in the local FederatedCode codebase.


.. _federatedcode_settings_config_dir:


FEDERATEDCODE_LOG_LEVEL
------------------------

By default, only a minimum of logging messages is displayed in the console.

Default: ``INFO``

The ``DEBUG`` value can be provided to this setting to see all FederatedCode debug
messages to help track down configuration issues for example.
This mode can be enabled globally through the ``.env`` file::

    FEDERATEDCODE_LOG_LEVEL=DEBUG

Or, in the context of running a :ref:`command <command_line_interface>`:

.. code-block:: console

    $ FEDERATEDCODE_LOG_LEVEL=DEBUG <command>

For instance, the web server can be started in DEBUG mode with:

.. code-block:: console

    $ FEDERATEDCODE_LOG_LEVEL=DEBUG make run


TIME_ZONE
---------

A string representing the time zone for the current FederatedCode installation. By
default the ``UTC`` time zone is used. Use it to set another zone::

    TIME_ZONE=Europe/Paris

.. note::
    You can view a detailed list of time zones `here.
    <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>`_

