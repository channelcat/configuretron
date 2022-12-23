"""Console script for configuretron."""
from base64 import b64encode, b64decode
import click
import json
import rsa
import sys
import yaml
from . import configuretron


def write_yaml(config_dict, yaml_path):
    out_yaml = yaml.dump(config_dict)
    click.echo(f"Saving YAML file {yaml_path}...", nl=False)
    try:
        open(yaml_path, "w").write(out_yaml)
    except Exception:
        click.echo("error writing to file")
        exit()
    click.echo("success")


@click.group()
@click.option("--yaml", "yaml_path", default=None, help="YAML configuration location")
@click.option("--private-key", default=None, help="Private key string")
@click.option("--private-key-file", default=None, help="Private key file path")
@click.option("--private-key-b64", default=None, help="Private key as a base64 string")
@click.option("--env", default=None, help="Environment to use")
@click.pass_context
def cli(ctx, yaml_path, private_key, private_key_file, private_key_b64, env):
    # -------- YAML --------
    if yaml_path is None and not "decrypt" in sys.argv:
        click.echo(f"Please provide a YAML configuration file location (--yaml=PATH before the provided command)")
        exit()

    ctx.ensure_object(dict)
    ctx.obj["yaml_path"] = yaml_path
    ctx.obj["env"] = env

    if yaml_path:
        click.echo(f"Loading YAML file {yaml_path}...", nl=False)
        try:
            ctx.obj["config"] = configuretron.yaml_to_dict(yaml_path)
        except Exception as e:
            click.echo(f"{e}")
            exit()

        click.echo(f"success")

    # -------- private key --------

    if private_key is not None:
        click.echo(f"Loading private key...", nl=False)
        ctx.obj["private_key"] = private_key
        click.echo(f"success")
    elif private_key_file is not None:
        click.echo(f"Reading private key file {private_key_file}...", nl=False)
        try:
            ctx.obj["private_key"] = open(private_key_file, "rb").read()
        except Exception as e:
            click.echo(f"Could not read private key file: {e}")
            exit()
        click.echo(f"success")
    elif private_key_b64 is not None:
        click.echo(f"Loading base64 private key...", nl=False)
        try:
            ctx.obj["private_key"] = b64decode(private_key_b64)
        except Exception as e:
            click.echo(f"Could not decode private key: {e}")
            exit()
        click.echo(f"success")
    else:
        ctx.obj["private_key"] = None


@cli.command()
@click.option(
    "--bits",
    type=int,
    default=2048,
    help="Number of bits used to generate the encryption key.  Higher numbers will result in higher generation times.",
)
@click.pass_context
def setup_encryption(ctx, bits):
    config_dict = ctx.obj["config"]
    yaml_path = ctx.obj["yaml_path"]

    # Validate key doesn't exist
    if "encryption" in config_dict and "key" in config_dict["encryption"]:
        click.echo("This configuration already includes an encryption key.")
        click.echo("Please remove encryption.key if you intend to overwrite it.")
        exit()

    if not "encyption" in config_dict:
        config_dict["encryption"] = {}

    # Generate pair
    click.echo(f"Generating {bits} bit RSA key pair...", nl=False)
    (key_public, key_private) = rsa.newkeys(bits, poolsize=8)
    config_dict["encryption"]["key"] = b64encode(key_public.save_pkcs1()).decode()
    click.echo("success")

    # Write to YAML
    write_yaml(config_dict, yaml_path)

    # Output private key
    private_key_pem = key_private.save_pkcs1()
    click.echo(f"\n===================")
    click.echo(f"=== Private Key ===")
    click.echo(f"===================\n")
    click.echo(f"Keep this secret and safe!  Without it you will not be able to decrypt any secrets:\n")
    click.echo(f"Code:")
    click.echo(f'   private_key = open("private_key.pem", "rb").read()\n')
    click.echo(f"Keyfile:\n")
    click.echo(private_key_pem)
    click.echo(f"\n============================")
    click.echo(f"=== Private Key B64 ENV  ===")
    click.echo(f"============================\n")
    click.echo(f"If passed as an environment variable (such as CONFIG_PRIVATE_KEY), use this base64 version instead\n")
    click.echo(f"Code:")
    click.echo(f'   private_key = configuretron.env_base64_value("CONFIG_PRIVATE_KEY")\n')
    click.echo(f"Key:\n")
    click.echo(b64encode(private_key_pem))


@cli.command()
@click.option("--key", default=None, help="Variable name to encrypt")
@click.argument("values", nargs=-1)
@click.pass_context
def encrypt(ctx, key=None, values=None):
    env = ctx.obj["env"]
    config_dict = ctx.obj["config"]
    config_args = config_dict["config"]
    yaml_path = ctx.obj["yaml_path"]

    # Validate key exists
    if "encryption" not in config_dict or "key" not in config_dict["encryption"]:
        click.echo("Encryption has not been set up for this configuration.  Please run setup_encryption.")
        exit()

    try:
        public_key_pem = b64decode(config_dict["encryption"]["key"])
        public_key = rsa.PublicKey.load_pkcs1(public_key_pem)
    except Exception:
        click.echo("Unable to process public key from config")

    if key:
        arg_source = config_args
        arg_source_name = "Config"
        if env:
            if "env" not in config_dict or env not in config_dict["env"]:
                click.echo(f"Env {env} not found in config")
                exit()
            arg_source = config_dict["env"][env]
            arg_source_name = f"Env {env}"

        if len(values) > 1:
            value = values
        elif values:
            value = values[0]
        else:
            if not key in arg_source:
                click.echo(f"{arg_source_name} is missing key {key}")
                exit()
            value = arg_source[key]

        click.echo(f"Encrypting {key} as {value}...", nl=False)
        arg_source[f"{key}.encrypted"] = configuretron.encrypt(value, public_key)
        click.echo(f"success")

        # Clear old key
        if key in arg_source:
            del arg_source[key]

        # Write to YAML
        write_yaml(config_dict, yaml_path)
    else:
        for value in values:
            click.echo(f"\n====================")
            click.echo(f"{value}")
            click.echo(f"====================")
            click.echo(f"{configuretron.encrypt(value, public_key)}")
            click.echo(f"====================")


@cli.command()
@click.argument("value")
@click.pass_context
def decrypt(ctx, value):
    if ctx.obj["private_key"] is None:
        click.echo(f"Please provide a private key (before the provided command)")
        exit()

    try:
        rsa_private_key = rsa.PrivateKey.load_pkcs1(ctx.obj["private_key"])
    except Exception as e:
        click.echo(f"Could not load private key: {e}")
        exit()

    try:
        value_decrypted = configuretron.decrypt(value, rsa_private_key)
    except Exception as e:
        click.echo(f"Error: {e}")
        exit()

    click.echo("Value:\n")
    click.echo(value_decrypted)


@cli.command()
@click.pass_context
def dump(ctx):
    try:
        config_args = configuretron.dict_to_args(
            config_dict=ctx.obj["config"], env=ctx.obj["env"], private_key=ctx.obj["private_key"]
        )
    except Exception as e:
        click.echo(f"Error: {e}")
        exit()
    click.echo(json.dumps(config_args, indent=4))


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
