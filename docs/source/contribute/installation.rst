.. _installation:

Installation
============

.. warning::
   FederatedCode is going through a major structural change and the
   installations are likely to not produce enough results.

Welcome to **FederatedCode** installation guide! This guide describes how to install
FederatedCode on various platforms.
Please read and follow the instructions carefully to ensure your installation is
functional and smooth.

The **preferred FederatedCode installation** is to :ref:`run_with_docker` as this is
the simplest to setup and get started.
Running FederatedCode with Docker **guarantees the availability of all features** with the
**minimum configuration** required.
This installation **works across all Operating Systems**.

Alternatively, you can install FederatedCode locally as a development server with some
limitations and caveats. Refer to the :ref:`local_development_installation` section.

.. _run_with_docker:

Run with Docker
---------------

Get Docker
^^^^^^^^^^

The first step is to download and **install Docker on your platform**.
Refer to Docker documentation and choose the best installation
path for your system: `Get Docker <https://docs.docker.com/get-docker/>`_.

Build the Image
^^^^^^^^^^^^^^^

FederatedCode is distributed with ``Dockerfile`` and ``docker-compose.yml`` files
required for the creation of the Docker image.

Clone the git `FederatedCode repo <https://github.com/nexB/federatedcode>`_,
create an environment file, and build the Docker image::

    git clone https://github.com/nexB/federatedcode.git && cd federatedcode
    make envfile
    docker-compose build

.. note::

    The image will need to be re-built when the FederatedCode app source code is
    modified or updated via
    ``docker-compose build --no-cache federatedcode``

Run the App
^^^^^^^^^^^

**Run your image** as a container::

    docker-compose up


At this point, the FederatedCode app should be running at port ``8000`` on your Docker host.
Go to http://localhost:8000/ on a web browser to access the web UI.
Optionally, you can set ``NGINX_PORT`` environment variable in your shell or in the `.env` file
to run on a different port than 8000.

.. note::

    To access a dockerized FederatedCode app from a remote location, the ``ALLOWED_HOSTS``
    and ``CSRF_TRUSTED_ORIGINS`` setting need to be provided in your ``docker.env`` file::

        ALLOWED_HOSTS=.domain.com,127.0.0.1
        CSRF_TRUSTED_ORIGINS=https://*.domain.com,http://127.0.0.1

    Refer to Django `ALLOWED_HOSTS settings <https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts>`_
    and `CSRF_TRUSTED_ORIGINS settings <https://docs.djangoproject.com/en/dev/ref/settings/#std-setting-CSRF_TRUSTED_ORIGINS>`_
    for more details.

.. warning::

   Serving FederatedCode on a network could lead to security issues and there
   are several steps that may be needed to secure such a deployment.
   Currently, this is not recommended.

.. _local_development_installation:


Local development installation
------------------------------

Supported Platforms
^^^^^^^^^^^^^^^^^^^

**FederatedCode** has been tested and is supported on the following operating systems:
    #. **Debian-based** Linux distributions

.. warning::
     On **Windows** FederatedCode can **only** :ref:`run_with_docker` and is not supported.

Pre-installation Checklist
^^^^^^^^^^^^^^^^^^^^^^^^^^

Before you install FederatedCode, make sure you have the following prerequisites:

 * **Python: 3.8+** found at https://www.python.org/downloads/
 * **Git**: most recent release available at https://git-scm.com/
 * **PostgreSQL**: release 10 or later found at https://www.postgresql.org/ or
   https://postgresapp.com/ on macOS

.. _system_dependencies:

System Dependencies
^^^^^^^^^^^^^^^^^^^

In addition to the above pre-installation checklist, there might be some OS-specific
system packages that need to be installed before installing FederatedCode.

On **Debian-based distros**, several **system packages are required** by FederatedCode.
Make sure those are installed::

    sudo apt-get install python3-venv python3-dev postgresql libpq-dev build-essential


Clone and Configure
^^^^^^^^^^^^^^^^^^^

Clone the `FederatedCode Git repository <https://github.com/nexB/federatedcode>`_::

    git clone https://github.com/nexB/federatedcode.git && cd federatedcode

Install the required dependencies::

    make dev

.. note::

    You can specify the Python version during the ``make dev`` step using the following
    command::

             make dev PYTHON_EXE=python3.8.10

    When ``PYTHON_EXE`` is not specified, by default, the ``python3`` executable is
    used.

Create an environment file::

    make envfile


Database
^^^^^^^^

**PostgreSQL** is the preferred database backend and should always be used on
production servers.

* Create the PostgreSQL user, database, and table with::

    make postgres

Tests
^^^^^

You can validate your federatedcode installation by running the tests suite::

    make test

Import a Service like ( VCIO , .. )
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create a Superuser::

    python manage.py createsuperuser

Create a Service:

using django-admin panel create user as service admin then create a Service 'vcio'
login using service admin credential then create a new git repository ex: https://github.com/nexB/vulnerablecode-data

Create a Sync request and Import git repository data:
click on the sync button under the git repository url then run: ``python manage.py tasks sync``


Web Application
^^^^^^^^^^^^^^^

A web application is available to create and manage your projects from a browser;
you can start the local webserver and access the app with::

    make run

Then open your web browser and visit: http://127.0.0.1:8000/ to access the web
application.

.. warning::
    This setup is **not suitable for deployments** and **only supported for local
    development**.


Upgrading
^^^^^^^^^

If you already have the FederatedCode repo cloned, you can upgrade to the latest version
with::

    cd federatedcode
    git pull
    make dev
    make migrate

