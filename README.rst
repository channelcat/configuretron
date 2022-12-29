==============
Configure-Tron
==============


.. image:: https://img.shields.io/pypi/v/configuretron.svg
        :target: https://pypi.python.org/pypi/configuretron

.. image:: https://img.shields.io/travis/channelcat/configuretron.svg
        :target: https://travis-ci.com/channelcat/configuretron

.. image:: https://readthedocs.org/projects/configuretron/badge/?version=latest
        :target: https://configuretron.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status


.. image:: https://pyup.io/repos/github/channelcat/configuretron/shield.svg
     :target: https://pyup.io/repos/github/channelcat/configuretron/
     :alt: Updates



Configuretron enables type hinted configuration files and secrets for python.  Easily add secrets to your configuration that are encryptable from clients and decryptable from trusted developers and running services.

Features
------------
 * Type-hinted configuration
 * Simple, readable YAML configs
 * Config in source control
 * Secrets safely in source control
 * Easily swap environments
 * Control who can encrypt and decrypt

Installation
------------

.. code-block:: console

    $ python -m pip install configuretron

Usage
--------

config.yml

.. code-block:: yaml

    config:
        api_url: https://apitopia.com/api/v1
        api_timeout: 20

config.py

.. code-block:: python

    @dataclass
    class Config:
        api_url: str
        api_timeout: int = 30

    config = configuretron.from_yaml(Config, "config.yml")

Adding Secrets
--------------

Adding encryption just takes a few console commands

.. code-block:: console

    $ python -m configuretron --yaml=config.yml setup_encryption

Copy the generated base64 private key into an environment variable (in this example, PRIVATE_KEY)

Encrypt and variables in the config (in this example, api_token):

.. code-block:: console

    $ python -m configuretron --yaml=config.yml encrypt --key api_token

Then pass the key to the config

.. code-block:: python

    private_key = configuretron.env_base64_value('PRIVATE_KEY')
    config = configuretron.from_yaml(Config, "config.yml", private_key=private_key)

Environmental overrides
-----------------------

To override values per-environment, add them into the config like so:

.. code-block:: yaml

    config:
        api_url: http://localhost:8080/api/v1
        api_timeout: 20
    env:
        prod:
            config:
                api_url: https://apitopia.com/api/v1

Then just pass `env` when initializing the configuration:

.. code-block:: python

    config = configuretron.from_yaml(Config, "config.yml", env="prod")


TODO Features
-------------
* Config heirarchy
* Type validation
* Multiple layered configs
