"""eBay OAuth configuration: URLs, scopes, and defaults."""

EBAY_SANDBOX = {
    "consent_url": "https://auth.sandbox.ebay.com/oauth2/authorize",
    "token_url": "https://api.sandbox.ebay.com/identity/v1/oauth2/token",
    "api_base": "https://api.sandbox.ebay.com",
}

EBAY_PRODUCTION = {
    "consent_url": "https://auth.ebay.com/oauth2/authorize",
    "token_url": "https://api.ebay.com/identity/v1/oauth2/token",
    "api_base": "https://api.ebay.com",
}

ENVIRONMENTS = {
    "sandbox": EBAY_SANDBOX,
    "production": EBAY_PRODUCTION,
}

SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.account.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly",
    "https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly",
]

RELAY_URL = "https://ebay-oauth-relay.fly.dev"

CALLBACK_PORT_RANGE = (8880, 8899)
DEFAULT_CALLBACK_PORT = 8881
CALLBACK_TIMEOUT_SECONDS = 300  # 5 minutes

KEYRING_SERVICE = "ebay-oauth"
KEYRING_ACCOUNT = "oauth-credentials"
