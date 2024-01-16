from base64 import b64decode, b64encode
import json
from os import environ, path
import rsa
from typing import Any, TypeVar
import yaml

T = TypeVar("T")
ENCRYPTION_DELIMETER = b"|"
ENCRYPTION_MAX_LENGTH = 245


def from_yaml(
    config_class: T,
    file: str,
    env: str = None,
    private_key: bytes = None,
    decrypt: bool = True,
) -> T:
    config_dict = yaml_to_dict(file)

    return from_dict(
        config_class=config_class,
        config_dict=config_dict,
        env=env,
        private_key=private_key,
        decrypt=decrypt,
    )


def from_dict(
    config_class: T,
    config_dict: dict,
    env: str = None,
    private_key: bytes = None,
    decrypt: bool = True,
) -> T:
    config_args = dict_to_args(
        config_dict=config_dict,
        env=env,
        private_key=private_key,
        decrypt=decrypt,
    )

    # Load data into dataclass
    try:
        config = config_class(**config_args)
    except Exception as e:
        raise ValueError(f"Configuration data does not match config class: {e}")

    return config


################### Loader Helpers ###################


def yaml_to_dict(file: str):
    if not path.exists(file):
        raise FileExistsError(f"Config file not found")

    # Load configuration
    try:
        with open(file) as config_file:
            config_string = config_file.read()
    except Exception as e:
        raise ValueError(f"Cannot read configuration file: {e}")

    # Parse YAML
    try:
        config_dict = yaml.load(config_string, Loader=yaml.FullLoader)
    except Exception as e:
        raise SyntaxError(f"Cannot parse configuration file: {e}")

    return config_dict


def dict_to_args(
    config_dict: dict,
    env: str = None,
    private_key: bytes = None,
    decrypt: bool = True,
):
    if not "config" in config_dict:
        raise KeyError("Config is missing config section")

    # Copy new config
    config_args = dict(config_dict["config"])

    # Layer environment data
    if env is not None:
        overlay_config_env(config_dict, config_args, env)

    # Decrypt Secrets
    if decrypt:
        if config_has_secrets(config_args):
            if not private_key:
                raise KeyError(
                    "Config has encrypted secrets, but no private key was provided"
                )
            try:
                rsa_private_key = rsa.PrivateKey.load_pkcs1(private_key)
            except Exception as e:
                raise KeyError(f"Private key provided was invalid: {e}")

            decrypt_config_keys(config_args, rsa_private_key)
    else:
        for key in list(config_args.keys()):
            if key.endswith(".encrypted"):
                config_args[key[:-10]] = None
                del config_args[key]

    return config_args


################### Config Helpers ###################


def config_has_secrets(config_args: dict):
    for key in config_args.keys():
        if key.endswith(".encrypted"):
            return True

    return False


def decrypt_config_keys(config_args: dict, private_key: rsa.PrivateKey):
    for key in list(config_args.keys()):
        if key.endswith(".encrypted"):
            decrypted_key = key[:-10]
            # Base64 decode
            try:
                config_args[decrypted_key] = decrypt(config_args[key], private_key)
            except Exception as e:
                raise ValueError(f"Key Error '{key}': {e}")

            del config_args[key]


def overlay_config_env(config_dict: dict, config_args: dict, env: str):
    for key in list(config_args.keys()):
        if not "env" in config_dict:
            raise KeyError("Config is missing env section")
        if not env in config_dict["env"]:
            raise KeyError(f"Config is missing {env} in env section")

        overlayed_env = config_dict["env"][env]
        if "config" in overlayed_env:
            overlayed_config = overlayed_env["config"]
            for key in overlayed_config.keys():
                config_args[key] = overlayed_config[key]


################### Value Encryption/Decryption ###################


def encrypt(value: Any, public_key: rsa.PublicKey):
    json_value = json.dumps(value).encode()

    encrypted_parts = []
    while json_value:
        encrypted_part = b64encode(
            rsa.encrypt(json_value[:ENCRYPTION_MAX_LENGTH], public_key)
        )
        encrypted_parts.append(encrypted_part)
        json_value = json_value[ENCRYPTION_MAX_LENGTH:]

    return (
        ENCRYPTION_DELIMETER.join(encrypted_parts)
        if len(encrypted_part) > 1
        else encrypted_part[0]
    )


def decrypt(value: str, private_key: rsa.PrivateKey):
    # TODO: make this always string or bytes
    value_parts = value.split(
        ENCRYPTION_DELIMETER.decode() if type(value) is str else ENCRYPTION_DELIMETER
    )
    decrypted_values = []
    for value_part in value_parts:
        # Base64 decode
        try:
            decoded_value = b64decode(value_part)
        except Exception as e:
            raise ValueError(f"Could not decode base64 encrypted: {e}")

        # RSA Decrypt
        try:
            decrypted_values.append(rsa.decrypt(decoded_value, private_key).decode())
        except Exception as e:
            raise ValueError(f"Could not decrypt with provided key: {e}")

    # Combine encrypted parts
    decrypted_value = (
        "".join(decrypted_values) if len(decrypted_values) > 1 else decrypted_values[0]
    )

    # JSON Load
    try:
        return json.loads(decrypted_value)
    except Exception as e:
        raise ValueError(f"Could not load JSON data: {e}")


################### Helpers ###################


def env_base64_value(key: str):
    """Helper to decode base64 environment variables such as private keys"""
    if not key in environ:
        raise KeyError(f"Missing key in environment: {key}")
    try:
        key_decoded = b64decode(environ.get(key))
    except Exception as e:
        raise ValueError(f"Could not decode environment variable {key}: {e}")

    return key_decoded
