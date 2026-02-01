"""CLI for eBay OAuth setup and token management."""

import base64
import os
import sys
import webbrowser
from urllib.parse import urlparse, parse_qs

import click
import httpx

from .config import RELAY_URL, ENVIRONMENTS
from .token_storage import store_credentials, get_credentials, delete_credentials
from .auth import EbayOAuthClient


def _exchange_code_for_tokens(code: str, environment: str, client_id: str, client_secret: str, runame: str) -> dict:
    """Exchange an authorization code for access + refresh tokens."""
    env_config = ENVIRONMENTS[environment]
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    response = httpx.post(
        env_config["token_url"],
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": runame,
        },
    )
    response.raise_for_status()
    return response.json()


@click.group()
def cli() -> None:
    """eBay OAuth CLI — setup and manage eBay API tokens."""
    pass


@cli.command()
@click.option("--environment", "-e", type=click.Choice(["sandbox", "production"]), default="sandbox",
              help="eBay environment to authenticate against.")
@click.option("--relay-url", default=RELAY_URL, help="OAuth relay URL.")
def setup(environment: str, relay_url: str) -> None:
    """Run the OAuth flow to get and store eBay tokens."""
    client_id = os.environ.get("EBAY_CLIENT_ID")
    client_secret = os.environ.get("EBAY_CLIENT_SECRET")
    runame = os.environ.get("EBAY_RUNAME", "")

    if not client_id or not client_secret:
        click.echo("Error: EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set as environment variables.", err=True)
        sys.exit(1)

    click.echo(f"Starting OAuth flow for eBay ({environment})...")

    # Build auth URL via relay
    auth_url = f"{relay_url}/auth/ebay?port=0&nonce=cli&environment={environment}"
    click.echo(f"\nOpening browser for eBay authorization...")
    click.echo(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # eBay sandbox redirects to its own success page instead of our callback.
    # Ask user to paste the URL from the success page.
    click.echo("After you approve access, eBay will show a success page.")
    click.echo("Copy the FULL URL from your browser's address bar and paste it here.\n")
    success_url = click.prompt("Paste the URL from the success page")

    # Extract the authorization code from the URL
    parsed = urlparse(success_url)
    params = parse_qs(parsed.query)

    code = params.get("code", [None])[0]
    if not code:
        error = params.get("error", ["unknown"])[0]
        click.echo(f"\nOAuth failed: {error}", err=True)
        sys.exit(1)

    click.echo("\nExchanging authorization code for tokens...")

    try:
        token_data = _exchange_code_for_tokens(code, environment, client_id, client_secret, runame)
    except Exception as e:
        click.echo(f"\nToken exchange failed: {e}", err=True)
        sys.exit(1)

    # Store credentials
    credentials = {
        "refresh_token": token_data["refresh_token"],
        "access_token": token_data.get("access_token"),
        "environment": environment,
        "client_id": client_id,
    }
    store_credentials(credentials)

    click.echo("\neBay OAuth tokens stored in OS keychain.")
    click.echo(f"Refresh token received (expires in {token_data.get('refresh_token_expires_in', 'unknown')}s)")
    click.echo("\nYou can now use ebay-oauth in your projects:")
    click.echo('  from ebay_oauth import EbayOAuthClient')


@cli.command()
def status() -> None:
    """Check if stored eBay credentials are valid."""
    creds = get_credentials()
    if not creds:
        click.echo("No credentials found in keychain.")
        click.echo("Run 'ebay-oauth setup' to authenticate.")
        sys.exit(1)

    click.echo(f"Environment: {creds.get('environment', 'unknown')}")
    click.echo(f"Client ID: {creds.get('client_id', 'unknown')}")
    click.echo(f"Refresh token: {'present' if creds.get('refresh_token') else 'missing'}")

    # Try to get an access token
    client_id = os.environ.get("EBAY_CLIENT_ID", creds.get("client_id", ""))
    client_secret = os.environ.get("EBAY_CLIENT_SECRET", "")
    refresh_token = creds.get("refresh_token", "")
    environment = creds.get("environment", "sandbox")

    if not client_secret:
        click.echo("\nSet EBAY_CLIENT_SECRET to test token refresh.")
        return

    try:
        client = EbayOAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            environment=environment,
        )
        client.get_access_token()
        click.echo("Access token: valid (refreshed successfully)")
    except Exception as e:
        click.echo(f"Access token: refresh failed ({e})")


@cli.command()
def refresh() -> None:
    """Force-refresh the access token."""
    creds = get_credentials()
    if not creds:
        click.echo("No credentials found. Run 'ebay-oauth setup' first.", err=True)
        sys.exit(1)

    client_id = os.environ.get("EBAY_CLIENT_ID", creds.get("client_id", ""))
    client_secret = os.environ.get("EBAY_CLIENT_SECRET", "")
    refresh_token = creds.get("refresh_token", "")
    environment = creds.get("environment", "sandbox")

    if not client_secret:
        click.echo("Error: EBAY_CLIENT_SECRET must be set.", err=True)
        sys.exit(1)

    try:
        client = EbayOAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            environment=environment,
        )
        token = client.force_refresh()
        click.echo(f"Access token refreshed successfully.")
        click.echo(f"Token: {token[:20]}...")
    except Exception as e:
        click.echo(f"Refresh failed: {e}", err=True)
        sys.exit(1)


@cli.command()
def logout() -> None:
    """Delete stored credentials from the keychain."""
    if delete_credentials():
        click.echo("Credentials deleted from keychain.")
    else:
        click.echo("No credentials found to delete.")
