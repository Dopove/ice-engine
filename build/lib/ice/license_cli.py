import os
import click
import sys
from .core.security import SecurityManager
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

@click.group()
def license():
    """Manage ICE software license."""
    pass

@license.command()
@click.option("--key", default=None, help="The ICE_LICENSE_JWT to store.")
def init(key):
    """Initializes the ICE license and generates a local machine keypair."""
    click.echo("🧊 ICE License Initialization")
    
    # Ensure machine keypair exists
    private_key, public_key = SecurityManager.get_machine_keypair()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    click.echo(f"✅ Cryptographic Machine Keypair (Fingerprint: {public_key_pem[:30]}...{public_key_pem[-30:]}) generated/loaded.")

    license_jwt = key or click.prompt("Please paste your Dopove-issued ICE_LICENSE_JWT", type=str)
    
    # Store the JWT locally
    home = os.path.expanduser("~")
    ice_dir = os.path.join(home, ".ice")
    os.makedirs(ice_dir, exist_ok=True)
    license_file = os.path.join(ice_dir, "license.jwt")
    with open(license_file, "w") as f:
        f.write(license_jwt)
    
    # Validate the license
    sec = SecurityManager(license_key=license_jwt)
    if sec.verify_license(license_jwt):
        click.secho(f"✅ License successfully initialized and validated. Stored at: {license_file}", fg="green")
        click.echo("🚀 You are ready to launch ICE.")
    else:
        click.secho("❌ License validation failed. Please check your JWT.", fg="red")
        if os.path.exists(license_file):
            os.remove(license_file) # Remove invalid license
        sys.exit(1)

@license.command()
def show():
    """Display current license status and machine keypair."""
    click.echo("--- ICE License Status ---")
    
    # Show machine keypair status
    try:
        _private_key, public_key = SecurityManager.get_machine_keypair()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        click.echo(f"Machine Keypair: ✅ Found (Fingerprint: {public_key_pem[:40]}...)")
    except FileNotFoundError:
        click.secho("Machine Keypair: ❌ Not found. Run 'ice license init'.", fg="red")

    # Show JWT license status
    jwt_token = os.getenv("ICE_LICENSE_JWT") or (
        open(os.path.expanduser("~/.ice/license.jwt")).read().strip() 
        if os.path.exists(os.path.expanduser("~/.ice/license.jwt")) 
        else None
    )

    if jwt_token:
        try:
            import jwt
            payload = jwt.decode(jwt_token, options={"verify_signature": False}) # Decode without verification for display
            click.secho("License JWT: ✅ Found and Decoded", fg="green")
            click.echo(f"  - Product: {payload.get('product')}")
            click.echo(f"  - Max Nodes: {payload.get('max_nodes')}")
            click.echo(f"  - Expires: {time.ctime(payload.get('exp'))}")
            click.echo(f"  - Bound to Machine Key: {'Yes' if 'machine_public_key' in payload else 'No'}")
        except Exception as e:
            click.secho(f"License JWT: ⚠️ Found but could not be decoded: {e}", fg="yellow")
    else:
        click.secho("License JWT: ❌ Not found. Run 'ice license init' or set ICE_LICENSE_JWT.", fg="red")

# This would be added to the main cli group in ice/cli.py
# main.add_command(license)
