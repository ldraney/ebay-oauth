# eBay OAuth

## What This Is

A Python CLI tool and library for eBay OAuth 2.0 Authorization Code Grant flow. Gets a refresh token, manages token lifecycle.

## Related Projects

- **[ebay-mcp-server](https://github.com/ldraney/ebay-mcp-server)** — MCP server for creating eBay listings via Claude. Depends on this package for auth.

## Two Interfaces

1. **CLI** — `ebay-oauth setup` runs the full OAuth flow and gives you a refresh token
2. **Library** — `EbayOAuthClient` provides `get_access_token()` with auto-refresh

## Key Commands

```bash
poetry add ebay-oauth    # or: pip install ebay-oauth
ebay-oauth setup          # interactive OAuth flow
ebay-oauth status         # check if token is valid
ebay-oauth refresh        # force token refresh
```

## Library Usage

```python
from ebay_oauth import EbayOAuthClient

client = EbayOAuthClient(
    client_id="...",
    client_secret="...",
    refresh_token="...",
    environment="sandbox"
)
token = client.get_access_token()  # auto-refreshes
```

## Environment Variables

- `EBAY_CLIENT_ID`
- `EBAY_CLIENT_SECRET`
- `EBAY_REFRESH_TOKEN`
- `EBAY_ENVIRONMENT` (sandbox | production)

## eBay OAuth Specifics

- Auth header: `Basic base64(client_id:client_secret)`
- Access token TTL: 2 hours
- Refresh token TTL: 18 months
- Sandbox token endpoint: `https://api.sandbox.ebay.com/identity/v1/oauth2/token`
- Production token endpoint: `https://api.ebay.com/identity/v1/oauth2/token`
- Sandbox consent: `https://auth.sandbox.ebay.com/oauth2/authorize`
- Production consent: `https://auth.ebay.com/oauth2/authorize`

## Deployment

- **Local mode** (default): localhost callback server, works for sandbox
- **fly.io mode** (`--remote`): for production eBay apps that require HTTPS redirect URIs

## Package Management

Uses **Poetry** for dependency management and publishing:

```bash
poetry install          # install deps
poetry run pytest       # run tests
poetry build            # build wheel + sdist
poetry publish          # publish to PyPI
```

## Testing

```bash
poetry run pytest tests/
```

Tests mock eBay API responses. No real eBay calls in unit tests.

## File Structure

```
ebay-oauth/
├── src/
│   └── ebay_oauth/
│       ├── __init__.py
│       ├── auth.py
│       ├── server.py
│       ├── cli.py
│       └── config.py
├── tests/
├── docs/
│   ├── architecture.html
│   ├── roadmap.html
│   └── user-story.html
├── fly.toml
├── pyproject.toml
└── CLAUDE.md
```
