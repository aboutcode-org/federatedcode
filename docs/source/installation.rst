.. _installation:

Installation
============

Welcome to **FederatedCode** installation guide. This guide describes how to install
FederatedCode. Please read and follow the instructions carefully to ensure
your installation is functional and operational.

The **preferred FederatedCode installation** is to :ref:`run_with_containers` as this is
the simplest to setup and get started.

Running FederatedCode with containers **guarantee the availability of all features** with the
**minimum configuration** required.
This installation **works across all Operating Systems** that duspport running Linux container
images, such as Docker, podman and related.

Alternatively, you can install FederatedCode locally as a development server with some
limitations and caveats. Refer to the :ref:`local_development_installation` section.

.. _run_with_containers:

Run with Containers
---------------------

Get Docker
^^^^^^^^^^

The first step is to download and **install Docker on your platform**.
Refer to Docker documentation and choose the best installation
path for your system: `Get Docker <https://docs.docker.com/get-docker/>`_.

.. note::
    We will eventually support other container runtimes beyond Docker, and they are likely to work
    out of the box but we have not yet tested these.


Build the Image
^^^^^^^^^^^^^^^^

FederatedCode distributed with ``Dockerfile`` and ``docker-compose.yml`` files
required for the creation of the base container image.

.. warning:: On **Windows**, ensure that git ``autocrlf`` configuration is set to
   ``false`` before cloning the repository::

    git config --global core.autocrlf false

**Clone the git** `FederatedCode repo <https://github.com/aboutcode-org/federatedcode>`_,
create an **environment file**, and **build the container image**::

    git clone https://github.com/aboutcode-org/federatedcode.git && cd federatedcode
    make envfile
    docker compose build

.. warning::
    As the ``docker-compose`` v1 command is officially deprecated by Docker, you will
    only find references to the ``docker compose`` v2 command in this documentation.

Run the App
^^^^^^^^^^^

**Run your image** as a container::

    docker compose up

At this point, the FederatedCode app should be running at port 80 on your Docker host.
Go to http://localhost/ on a web browser to **access the web UI**.

An overview of the web application usage is available at :ref:`user_interface`.

.. note::
    Congratulations, you are now ready to use FederatedCode.

.. warning::
    To access a containerized FederatedCode app from a remote location, the ``ALLOWED_HOSTS``
    and ``CSRF_TRUSTED_ORIGINS`` settings need to be provided in your ``.env`` file,
    for example::

        ALLOWED_HOSTS=.your-domain.com
        CSRF_TRUSTED_ORIGINS=https://*.your-domain.com

    Refer to `ALLOWED_HOSTS settings <https://docs.djangoproject.com/
    en/dev/ref/settings/#allowed-hosts>`_ and `CSRF_TRUSTED_ORIGINS settings
    <https://docs.djangoproject.com/en/dev/ref/settings/
    #std-setting-CSRF_TRUSTED_ORIGINS>`_ for more details.

.. tip::
    If you run FederatedCode on desktop or laptop, it may come handy to pause/unpause
    or suspend your local FederatedCode system. For this, use these commands::

        docker compose pause  # to pause/suspend
        docker compose unpause  # to unpause/resume

Upgrade the App
^^^^^^^^^^^^^^^

**Update your local** `FederatedCode repo <https://github.com/aboutcode-org/federatedcode>`_,
and **re build the base container image**::

    cd federatedcode
    git pull
    docker compose build

.. warning::
    The container image has been updated to run as a non-root user.
    If you encounter "permissions" issues while running the FederatedCode container images following
    the ``docker compose build``, you will need to update the the permissions of the
    ``/var/federatedcode/`` directory of the Docker volumes using::

        docker compose run -u 0:0 web chown -R app:app /var/federatedcode/

    See also a related issue in ScanCode.io to run as non-root user
    https://github.com/aboutcode-org/scancode.io/issues/399

.. note::
    You need to rebuild the image whenever FederatedCode's source code has been
    modified or updated.

Execute a Command
^^^^^^^^^^^^^^^^^

.. note::
    Refer to the :ref:`command_line_interface` section for the full list of commands.



.. _local_development_installation:

Local development installation
------------------------------

Supported Platforms
^^^^^^^^^^^^^^^^^^^

**FederatedCode** has been tested and is supported on the following operating systems:

    #. **Debian-based** Linux distributions

.. note::
    **macOS**, **Windows**, and other **Linux** distributions are likely working too, but have
    not been tested.

.. warning::
     On **Windows** FederatedCode can **only** be :ref:`run_with_containers`.

Pre-installation Checklist
^^^^^^^^^^^^^^^^^^^^^^^^^^

Before you install FederatedCode, make sure you have the following prerequisites:

 * **Python: versions 3.8 to 3.11** found at https://www.python.org/downloads/
 * **Git**: most recent release available at https://git-scm.com/
 * **PostgreSQL**: release 11 or later found at https://www.postgresql.org/ (or
   https://postgresapp.com/ on macOS)

.. _system_dependencies:

System Dependencies
^^^^^^^^^^^^^^^^^^^

In addition to the above pre-installation checklist, there might be some OS-specific
system packages that need to be installed before installing FederatedCode.

On **Linux**, some **system packages are required**.
Make sure those are installed before attempting a local FederatedCode installation::

    sudo apt-get install \
        build-essential python3-dev libssl-dev libpq-dev \
        bzip2 xz-utils zlib1g libxml2-dev libxslt1-dev libpopt0


Clone and Configure
^^^^^^^^^^^^^^^^^^^

 * Clone the `FederatedCode GitHub repository <https://github.com/aboutcode-org/federatedcode>`_::

    git clone https://github.com/aboutcode-org/federatedcode.git && cd federatedcode

 * Inside the :guilabel:`federatedcode/` directory, install the required dependencies::

    make dev

 .. note::
    You can specify the Python version during the ``make dev`` step using the following
    command::

        make dev PYTHON_EXE=python3.11

    When ``PYTHON_EXE`` is not specified, by default, the ``python3`` executable is
    used.


 * Create an environment file::

    make envfile


Database
^^^^^^^^

**PostgreSQL** is the preferred database backend and should always be used on production servers.

* Create the PostgreSQL user, database, and table with::

    make postgresdb

.. warning::
    The ``make postgres`` command is assuming that your PostgreSQL database template is
    using the ``en_US.UTF-8`` collation.
    If you encounter database creation errors while running this command, it is
    generally related to an incompatible database template.

    You can either `update your template <https://stackoverflow.com/a/60396581/8254946>`_
    to fit the FederatedCode default, or provide custom values collation using the
    ``POSTGRES_INITDB_ARGS`` variable such as::

        make postgresdb POSTGRES_INITDB_ARGS=\
            --encoding=UTF-8 --lc-collate=en_US.UTF-8 --lc-ctype=en_US.UTF-8


Tests
^^^^^

You can validate your FederatedCode installation by running the tests suite::

    make test

Web Application
^^^^^^^^^^^^^^^

A web application is available to create and manage your projects from a browser;
you can start the local webserver and access the app with::

    make run

Then open your web browser and visit: http://localhost:8001/ to access the web
application.

.. warning::
    This setup is **not suitable for production deployments** and **only supported for local
    development**.
    It is highly recommended to use the :ref:`run_with_containers` setup to ensure the
    availability of all the features.

An overview of the web application usage is available at :ref:`user_interface`.

Upgrading
^^^^^^^^^

If you already have the FederatedCode repo cloned, you can upgrade to the latest version
with::

    cd federatedcode
    git pull
    make dev
    make migrate

