==============
FederatedCode
==============

FederatedCode is a decentralized, federated metadata system for open source software code and
security information.


Quick Installation
--------------------

On a Debian system, use this::

    sudo apt-get install python3-venv python3-dev postgresql libpq-dev build-essential
    git clone https://github.com/nexB/federatedcode.git
    cd federatedcode
    make dev envfile postgresdb
    make test
    source venv/bin/activate
    make run

Configuration
-------------------

The configuration of FederatedCode depends on environment variables:


- FEDERATEDCODE_WORKSPACE_LOCATION: Directory location of the workspace where we store local Git repos and
  content. Default to var/ in current directory in development
- FEDERATEDCODE_CLIENT_ID:
- FEDERATEDCODE_CLIENT_SECRET: Generated id and secret stored in a .env file 


Acknowledgements
^^^^^^^^^^^^^^^^

This project is funded through the NGI0 Entrust Fund, a fund established by NLnet with financial
support from the European Commission's Next Generation Internet programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No 101069594.

https://nlnet.nl/project/FederatedSoftwareMetadata/

This project also receives support and funding from Google and nexB.

