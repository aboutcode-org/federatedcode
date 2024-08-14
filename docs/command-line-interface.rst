.. _command_line_interface:

Command Line Interface
======================

A command can be executed through the ``docker compose`` command line
interface with::

    docker compose exec -it federatedcode <COMMAND>

Alternatively, you can start a ``bash`` session in a new Docker container to execute
multiple ``federatedcode`` commands::

    docker compose run federatedcode bash
    COMMAND
    COMMAND
    ...

.. warning::
    In order to add local input files to a project using the Command Line Interface,
    extra arguments need to be passed to the ``docker compose`` command.

    For instance ``--volume /path/on/host:/target/path/in/container:ro``
    will mount and make available the host path inside the container (``:ro`` stands
    for read only).

    .. code-block:: bash

        docker compose run --volume /home/sources:/sources:ro \
            web scanpipe create-project my_project --input-file="/sources/image.tar"

.. note::
    In a local development installation, the ``scanpipe`` command is directly
    available as an entry point in your virtualenv and is located at
    ``<scancode.io_root_dir>/bin/scanpipe``.
