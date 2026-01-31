# User Story

## Who
A developer building tools that interact with the eBay API on behalf of a seller (e.g., an MCP server for AI-powered listing).

## Problem
eBay's OAuth Authorization Code Grant flow requires:
1. A publicly accessible HTTPS endpoint to receive the callback
2. Understanding eBay's specific OAuth quirks (Base64-encoded credentials, scope formatting, sandbox vs production URLs)
3. Manual token exchange and refresh logic

This is a one-time setup task that blocks all other development. Every eBay API project hits this wall first.

## Desired Experience

```
$ pip install ebay-oauth
$ ebay-oauth setup
```

The CLI:
1. Asks for client_id, client_secret, and environment (sandbox/production)
2. Spins up a temporary local server or deploys a callback handler to fly.io
3. Opens the browser to eBay's consent page
4. Catches the callback, exchanges the code for tokens
5. Prints the refresh token and optionally writes it to a `.env` file

From that point forward, the developer has a long-lived refresh token (18 months) and never thinks about OAuth again until it expires.

## Secondary Use: Library

For developers who want token management in their own apps:

```python
from ebay_oauth import EbayOAuthClient

client = EbayOAuthClient(
    client_id="...",
    client_secret="...",
    refresh_token="...",
    environment="sandbox"  # or "production"
)

# Always returns a valid access token (auto-refreshes if expired)
token = client.get_access_token()
```

## Success Criteria
- `pip install ebay-oauth` works
- `ebay-oauth setup` gets a refresh token in under 2 minutes
- Token auto-refresh works transparently
- Works with both sandbox and production eBay environments
