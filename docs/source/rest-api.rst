.. _rest_api:

REST API
========

To get started with the REST API, visit the **API endpoints** at
http://localhost/api/ or http://localhost:8001/api/ if you run on a
local development setup.

.. _rest_api_authentication:

Authentication
--------------

When the authentication setting :ref:`federatedcode_settings_require_authentication`
is enabled on a FederatedCode instance (disabled by default), you will have to include
an authentication token ``API key`` in the Authorization HTTP header of each request.

The key should be prefixed by the string literal "Token" with whitespace
separating the two strings. For example::

    Authorization: Token abcdef123456

.. warning::
    Your API key is like a password and should be treated with the same care.

Example of a cURL-style command line using an API Key for authentication:

.. code-block:: console

    curl -X GET http://localhost/api/ -H "Authorization:Token abcdef123456"

Example of a Python script:

.. code-block:: python

    import requests

    api_url = "http://localhost/api/"
    headers = {
        "Authorization": "Token abcdef123456",
    }
    params = {
        "page": "2",
    }
    response = requests.get(api_url, headers=headers, params=params)
    response.json()

