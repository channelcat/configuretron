from base64 import b64decode, b64encode
import json
from os import environ, path
import rsa
from typing import Any, TypeVar
import yaml

T = TypeVar("T")


def from_yaml(config_class: T, file: str, env: str = None, private_key: bytes = None) -> T:
    config_dict = yaml_to_dict(file)

    return from_dict(config_class=config_class, config_dict=config_dict, env=env, private_key=private_key)


def from_dict(config_class: T, config_dict: dict, private_key: bytes = None, env: str = None) -> T:
    config_args = dict_to_args(config_dict=config_dict, env=env, private_key=private_key)

    # Load data into dataclass
    try:
        config = config_class(**config_args)
    except Exception as e:
        raise ValueError(f"Configuration data does not match config class: {e}")

    return config


################### Loader Helpers ###################


def yaml_to_dict(file: str):
    if not path.exists(file):
        raise FileExistsError(f"Cannot read configuration file: {e}")

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


def dict_to_args(config_dict: dict, private_key: bytes = None, env: str = None):
    if not "config" in config_dict:
        raise KeyError("Config is missing config section")

    # Copy new config
    config_args = dict(config_dict["config"])

    # Layer environment data
    if env is not None:
        overlay_config_env(config_dict, config_args, env)

    # Decrypt Secrets
    if config_has_secrets(config_args):
        if not private_key:
            raise KeyError("Config has encrypted secrets, but no private key was provided")
        try:
            rsa_private_key = rsa.PrivateKey.load_pkcs1(private_key)
        except Exception as e:
            raise KeyError(f"Private key provided was invalid: {e}")

        decrypt_config_keys(config_args, rsa_private_key)

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

        overlayed_config = config_dict["env"][env]
        for key in overlayed_config.keys():
            config_args[key] = overlayed_config[key]


################### Value Encryption/Decryption ###################


def encrypt(value: Any, public_key: rsa.PublicKey):
    return b64encode(rsa.encrypt(json.dumps(value).encode(), public_key)).decode()


def decrypt(value: str, private_key: rsa.PrivateKey):
    # Base64 decode
    try:
        decoded_value = b64decode(value)
    except Exception as e:
        raise ValueError(f"Could not decode base64 encrypted: {e}")

    # RSA Decrypt
    try:
        decrypted_value = rsa.decrypt(decoded_value, private_key).decode()
    except Exception as e:
        raise ValueError(f"Could not decrypt with provided key: {e}")

    # JSON Load
    try:
        result = json.loads(decrypted_value)
    except Exception as e:
        raise ValueError(f"Could not load JSON data: {e}")

    return result


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
