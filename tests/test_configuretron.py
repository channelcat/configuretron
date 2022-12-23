#!/usr/bin/env python

"""Tests for `configuretron` package."""

import pytest

from click.testing import CliRunner

from configuretron import configuretron
from configuretron import cli
from dataclasses import dataclass
import os.path


@dataclass
class BasicConfig:
    some_int: int
    some_float: float
    some_dict: dict
    some_list_numbers: list[int]
    some_list_strings: list[str]
    test_inherit: str
    test_override: str


@dataclass
class EncryptedConfig:
    secret: str
    secret_list: list[int]


private_key = b"-----BEGIN RSA PRIVATE KEY-----\nMIIEqwIBAAKCAQEAh7OC5Ki6VssdeRoGiQSKQs9BULEAQXHCoq7lnfmgzQ6gSlSw\nd9vBxU0zrv8eGZRGzKFM0C8i7RU4kEf8QhYrfMu8noclBlqQzPOy8uKBHOsL6Z5v\nCAt01KP8REC5UG4Aj3zEADsO4Ne/vTWkdNQi8y/zOt5lC7TJ3Hkpa/3KvVVNKZcZ\nJcyQcDRc2IKbaSnlN2WdyjkzgZ6LQ6mLl961++kBDdmFXgyaeREFJpIsq+QUGYZz\nvsK8bUqL2tCbeaX/ZaDhgjEnjk6KzO66tvgBT8OuYjbukiwdeyfCMamAuB4BMLO1\nmCWi5u99K5xfVA176abjWxyYup5JWMKNbOurgwIDAQABAoIBAAwBX6UnIEUpdxQN\nr2JT2n+KonanEiS4EcYevwW43fcGQjwRPgN8l6oC6H2k6F7O9WyJIKiSYv6ij/yD\nwdd+6p4B0FAeGLJ1NLZNIRnH3DBYwxcKAzys9ssRLvJC36Iz+Sy4lwaGMwzFSZtN\nsZz8X5MwPM6KeloMxnYn8xKJjAT2pGjhBnI6g+G+XeWEl9AW55FFLvPIypRv9Lcz\nURhHhR5wJMaRuReSwSqJLO1CUVd71mrxIMGhFLhDAA3/r4fPuywYlmzhGINLhDni\nWWIioM6OMJosskpv9cmyi/EzhBhCnfC5C7PtLLqmtWneEkJEsxhAZXHAnKk+Oc2R\n66A35oECgYkAvyMvflTs+tp+uTOEvNlGgv/RuSZQkVU7VFQOTxWkOseZD5bdRDYc\niKtX7w855zSxr+zEVI/H8dnfh0LKTMSU3joS/4TiwWe+bNYQqLzYimV7sg9gJjhK\nbiGXcPgt4QYNUhjCMFxwTntU3FewtJs+MZskYXRm+NbGPYRQQ5ZGGfvkG+GB6IiJ\n4wJ5ALXAYFUUrmIlPkGAP+WNdNLVRrREuvMoEROpWo0zpxC+9bihrFX+NjwaT1ki\nNwLoXEzyrNuuf5VHx3CLMwSgxQj1by36jhlkWdzDH6MMUggeCiL5INmtyMxYSoOP\nwHG6G7OJxjSBChsvq3N6AZ9LkcJ+JjJSgmCJ4QKBiQCYZdeSZOhmwxvTUu59HMiJ\n3qs7cv8+QbUCcdrO17SQYWD6+xEFOBfcKLH+HCfQ30TlvmR0AAguH8eIM4rVVtBT\nt/452ZxrFOrSIIQ75gbJokzUFkpVbwB5ezMikd8S0h6A3NjIcovhJ5jr7scn2bfn\nGYoSYhtQQP7jQcI1gXX3dc3VJSLNY0B9AnkAsAv/Q2oc34QjoV6QhdFW70EWk1Zf\nn1eX8ut/gnYdxOKzMHupakIqVl1FrpitoGthvEbzmHaVrgsw65ppeHohYGQbpPWk\n3oONZ4C5DD3K14IBX47gevkSHp0G0BhV19LlMiqpigHTwDGUaO4s1BdmwHVgmi3B\ni7EBAoGJAJItwE1Qi2fyIUNb6UQEbOrbXAN695JlojW7HvZ7cmQ0KYMD99/c2KIj\nhxA9CpZE/ukE4I203fasX9J2eb/oESfabC46Pau2k1pnW8t9XZx58qqX1pDlq/mT\nGJyyOZPuVVzaAabsjRfoYEHQM4Jm+IyH7h/c/ZcdYCTanLKuia1eDHCD6b+9LSA=\n-----END RSA PRIVATE KEY-----\n"

test_dir = os.path.dirname(os.path.realpath(__file__))
BASIC_CONFIG_YAML = os.path.join(test_dir, "config_basic.yml")
ENCRYPTED_CONFIG_YAML = os.path.join(test_dir, "config_encrypted.yml")


def test_basic_configuration():
    config = configuretron.from_yaml(BasicConfig, BASIC_CONFIG_YAML)
    assert config.some_int == 12345
    assert config.some_float == 1.11
    assert config.some_dict == {"key": "value", "other": "out"}
    assert config.some_list_numbers == [1, 2, 3]
    assert config.some_list_strings == ["wow", "it's a", "list"]
    assert config.test_inherit == "inherited"
    assert config.test_override == "global"


def test_environment_override():
    basic_config = configuretron.from_yaml(BasicConfig, BASIC_CONFIG_YAML)
    prod_config = configuretron.from_yaml(BasicConfig, BASIC_CONFIG_YAML, "prod")
    assert basic_config.test_inherit == "inherited"
    assert basic_config.test_override == "global"
    assert prod_config.test_inherit == "inherited"
    assert prod_config.test_override == "prod"


def test_encryption():
    config = configuretron.from_yaml(EncryptedConfig, ENCRYPTED_CONFIG_YAML, private_key=private_key)
    assert config.secret == "secret"
    assert config.secret_list == [1, 2, 3]


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.cli)
    assert result.exit_code == 0
    assert "Usage: " in result.output
    help_result = runner.invoke(cli.cli, ["--help"])
    assert help_result.exit_code == 0
