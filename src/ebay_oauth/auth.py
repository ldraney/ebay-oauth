"""eBay OAuth client with automatic token refresh."""

import base64
import time

import httpx

from .config import ENVIRONMENTS


class EbayOAuthClient:
    """OAuth client that manages access token lifecycle.

    Usage:
        client = EbayOAuthClient(
            client_id="...",
            client_secret="...",
            refresh_token="...",
            environment="sandbox",
        )
        token = client.get_access_token()  # auto-refreshes when expired
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        environment: str = "sandbox",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.environment = environment

        env_config = ENVIRONMENTS.get(environment)
        if not env_config:
            raise ValueError(f"Unknown environment: {environment}. Use 'sandbox' or 'production'.")
        self.token_url = env_config["token_url"]
        self.api_base = env_config["api_base"]

        self._access_token: str | None = None
        self._token_expiry: float = 0

    def _basic_auth_header(self) -> str:
        """Generate Basic auth header value: base64(client_id:client_secret)."""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def get_access_token(self) -> str:
        """Get a valid access token, refreshing if expired.

        Returns:
            A valid eBay access token string.

        Raises:
            httpx.HTTPStatusError: If the token refresh request fails.
            RuntimeError: If the response doesn't contain an access token.
        """
        # Return cached token if still valid (with 60s buffer)
        if self._access_token and time.time() < (self._token_expiry - 60):
            return self._access_token

        return self._refresh_access_token()

    def _refresh_access_token(self) -> str:
        """Exchange the refresh token for a new access token."""
        with httpx.Client() as client:
            response = client.post(
                self.token_url,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": self._basic_auth_header(),
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
            )
            response.raise_for_status()

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise RuntimeError(f"No access_token in response: {data}")

        self._access_token = access_token
        expires_in = data.get("expires_in", 7200)
        self._token_expiry = time.time() + int(expires_in)

        return access_token

    def force_refresh(self) -> str:
        """Force a token refresh regardless of expiry."""
        self._access_token = None
        self._token_expiry = 0
        return self._refresh_access_token()
