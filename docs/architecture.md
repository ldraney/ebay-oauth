# Architecture

## Overview

`ebay-oauth` is two things:
1. **A CLI tool** — runs `ebay-oauth setup` to complete the OAuth flow and obtain a refresh token
2. **A Python library** — provides `EbayOAuthClient` for token management (auto-refresh, caching)

## OAuth Flow

```
Developer          CLI / Local Server          eBay
   |                     |                       |
   | ebay-oauth setup    |                       |
   |-------------------->|                       |
   |                     | start localhost:8080   |
   |                     |                       |
   |  browser opens      |                       |
   |-------------------->|---consent URL--------->|
   |                     |                       |
   |                     |    user authorizes     |
   |                     |                       |
   |                     |<--redirect + code------|
   |                     |                       |
   |                     |---exchange code------->|
   |                     |<--access + refresh-----|
   |                     |                       |
   | refresh token       |                       |
   |<--------------------|                       |
   | (printed + .env)    |                       |
```

## Components

### `ebay_oauth/auth.py` — Token Management
- `EbayOAuthClient` class
- Holds client credentials + refresh token
- `get_access_token()` — returns cached token or refreshes if expired
- Handles eBay's auth header format: `Basic base64(client_id:client_secret)`
- Knows sandbox vs production URLs

### `ebay_oauth/server.py` — Callback Server
- Minimal HTTP server (stdlib `http.server` or Flask — TBD)
- One route: `/callback` — receives the authorization code from eBay
- Exchanges code for tokens via eBay's token endpoint
- Shuts down after receiving the token

### `ebay_oauth/cli.py` — CLI Entry Point
- `setup` command — orchestrates the full OAuth flow
- Prompts for credentials (or reads from env/args)
- Starts the callback server
- Opens the browser
- Prints the refresh token, optionally writes `.env`
- `refresh` command — manually force a token refresh (debugging)
- `status` command — check if current refresh token is still valid

### `ebay_oauth/config.py` — URLs and Constants
- Sandbox vs production URL mapping
- OAuth endpoint paths
- Default scopes

## Deployment Modes

### Mode 1: Local (default for `ebay-oauth setup`)
- Starts a server on `localhost:8080`
- Works for eBay sandbox (accepts `http://localhost` redirect URIs)
- For production: requires the developer to set their eBay app's redirect URI to `https://your-app.fly.dev/callback` and use Mode 2

### Mode 2: fly.io (for production eBay apps)
- The same callback server, deployed to fly.io
- `ebay-oauth setup --remote` triggers this path
- Alternatively, deploy manually: `fly launch` with the included `fly.toml`
- The fly.io app receives the callback, displays the refresh token, and can be torn down

## eBay-Specific Details

### Token Endpoint
- Sandbox: `https://api.sandbox.ebay.com/identity/v1/oauth2/token`
- Production: `https://api.ebay.com/identity/v1/oauth2/token`

### Consent URL
- Sandbox: `https://auth.sandbox.ebay.com/oauth2/authorize`
- Production: `https://auth.ebay.com/oauth2/authorize`

### Auth Header
eBay wants: `Authorization: Basic <base64(client_id:client_secret)>`
This is standard HTTP Basic auth but developers frequently get it wrong because eBay docs are confusing.

### Scopes
Space-separated in the consent URL. Common set:
```
https://api.ebay.com/oauth/api_scope/sell.inventory
https://api.ebay.com/oauth/api_scope/sell.fulfillment
https://api.ebay.com/oauth/api_scope/commerce.taxonomy.readonly
https://api.ebay.com/oauth/api_scope/buy.browse
```

### Token Lifetimes
- Access token: 2 hours
- Refresh token: 18 months

## Package Structure

```
ebay-oauth/
├── src/
│   └── ebay_oauth/
│       ├── __init__.py       # exports EbayOAuthClient
│       ├── auth.py           # token management
│       ├── server.py         # callback server
│       ├── cli.py            # CLI commands
│       └── config.py         # URLs, constants
├── tests/
│   ├── test_auth.py
│   ├── test_server.py
│   └── test_cli.py
├── docs/
│   ├── architecture.md
│   ├── roadmap.md
│   └── user-story.md
├── fly.toml
├── pyproject.toml
├── CLAUDE.md
└── .gitignore
```
