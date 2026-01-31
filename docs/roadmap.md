# Roadmap

## Phase 1: Core Auth Library
- [ ] `EbayOAuthClient` class with token refresh
- [ ] Sandbox + production URL handling
- [ ] Unit tests with mocked eBay responses
- [ ] Basic error handling (expired refresh token, invalid credentials, network errors)

## Phase 2: CLI + Local OAuth Flow
- [ ] `ebay-oauth setup` command — full local OAuth flow
- [ ] Localhost callback server
- [ ] Browser auto-open to consent URL
- [ ] Token display + `.env` file writing
- [ ] `ebay-oauth status` — validate current token
- [ ] Works end-to-end against eBay sandbox

## Phase 3: PyPI Release
- [ ] `pyproject.toml` with proper metadata
- [ ] Package as `ebay-oauth` on PyPI
- [ ] CLI entry point via `[project.scripts]`
- [ ] Minimal README with install + usage instructions

## Phase 4: fly.io Deployment Support
- [ ] `fly.toml` for one-click deployment
- [ ] `ebay-oauth setup --remote` for production eBay apps
- [ ] Instructions for fly.io deploy + teardown
- [ ] Production eBay environment tested

## Phase 5: Integration with ebay-mcp-server
- [ ] ebay-mcp-server imports `ebay_oauth.EbayOAuthClient`
- [ ] Transparent token management inside the MCP server
- [ ] First real listing posted via the full pipeline

## Out of Scope (for now)
- Web UI / dashboard
- Multi-user / multi-seller support
- Token persistence in a database
- Automatic fly.io deployment from CLI
