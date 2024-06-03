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

The database can be configured using the following settings::

    FEDERATEDCODE_DB_HOST=localhost
    FEDERATEDCODE_DB_NAME=federatedcode
    FEDERATEDCODE_DB_USER=user
    FEDERATEDCODE_DB_PASSWORD=password
    FEDERATEDCODE_DB_PORT=5432

.. _federatedcode_settings_require_authentication:

FEDERATEDCODE_REQUIRE_AUTHENTICATION
-----------------------------------------

By default, the FederatedCode Web UI and REST API are available without any
authentication.

The authentication system can be enable with this settings::

    FEDERATEDCODE_REQUIRE_AUTHENTICATION=True

Once enabled, all the Web UI views and REST API endpoints will force the user to login
to gain access.

A management command :ref:`cli_create_user` is available to create users and
generate their API key for authentication.

See :ref:`rest_api_authentication` for details on using the ``API key``
authentication system in the REST API.

.. _federatedcode_settings_workspace_location:

FEDERATEDCODE_WORKSPACE_LOCATION
-----------------------------------

This setting defines the workspace location of a given project.
The **workspace** is the directory where **all of the project's files are stored**
, such as input, codebase, and output files::

    FEDERATEDCODE_WORKSPACE_LOCATION=/var/federatedcode/workspace/

It defaults to a :guilabel:`var/` directory in the local FederatedCode codebase.

See :ref:`project_workspace` for more details.

.. _federatedcode_settings_config_dir:

FEDERATEDCODE_CONFIG_DIR
------------------------------

The location of the :guilabel:`.scancode/` configuration directory within the project
codebase.

Default: ``.scancode``

This directory allows to provide configuration files and customization for a FederatedCode
project directly through the codebase files.

For example, to provide a custom attribution template to your project, add it in a
:guilabel:`.scancode/` directory located at the root of your codebase before uploading
it to FederatedCode. The expected location of the attribution template is::

  .scancode/templates/attribution.html


FEDERATEDCODE_PAGINATE_BY
-------------------------------

The number of objects display per page for each object type can be customized with the
following setting::

    FEDERATEDCODE_PAGINATE_BY=project=30,error=50,resource=100,package=100,dependency=100

FEDERATEDCODE_REST_API_PAGE_SIZE
---------------------------------------

A numeric value indicating the number of objects returned per page in the REST API::

    FEDERATEDCODE_REST_API_PAGE_SIZE=100

Default: ``50``

.. warning::
    Using a large page size may have an impact on performances.

FEDERATEDCODE_LOG_LEVEL
------------------------

By default, only a minimum of logging messages is displayed in the console, mostly
to provide some progress about pipeline run execution.

Default: ``INFO``

The ``DEBUG`` value can be provided to this setting to see all FederatedCode debug
messages to help track down configuration issues for example.
This mode can be enabled globally through the ``.env`` file::

    FEDERATEDCODE_LOG_LEVEL=DEBUG

Or, in the context of running a :ref:`scanpipe command <command_line_interface>`:

.. code-block:: console

    $ FEDERATEDCODE_LOG_LEVEL=DEBUG bin/scanpipe [command]

The web server can be started in DEBUG mode with:

.. code-block:: console

    $ FEDERATEDCODE_LOG_LEVEL=DEBUG make run

TIME_ZONE
---------

A string representing the time zone for the current FederatedCode installation. By
default the ``UTC`` time zone is used::

    TIME_ZONE=Europe/Paris

.. note::
    You can view a detailed list of time zones `here.
    <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>`_

.. _federatedcode_settings_purldb:

