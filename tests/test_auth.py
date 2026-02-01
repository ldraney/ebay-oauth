"""Tests for EbayOAuthClient token refresh."""

import time
from unittest.mock import patch, MagicMock

import pytest
import httpx

from ebay_oauth.auth import EbayOAuthClient


@pytest.fixture
def client():
    return EbayOAuthClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        refresh_token="test_refresh_token",
        environment="sandbox",
    )


class TestEbayOAuthClient:
    def test_init_sandbox(self, client):
        assert client.environment == "sandbox"
        assert "sandbox" in client.token_url
        assert client._access_token is None

    def test_init_production(self):
        client = EbayOAuthClient(
            client_id="id",
            client_secret="secret",
            refresh_token="token",
            environment="production",
        )
        assert "sandbox" not in client.token_url
        assert client.api_base == "https://api.ebay.com"

    def test_init_invalid_environment(self):
        with pytest.raises(ValueError, match="Unknown environment"):
            EbayOAuthClient(
                client_id="id",
                client_secret="secret",
                refresh_token="token",
                environment="invalid",
            )

    def test_basic_auth_header(self, client):
        header = client._basic_auth_header()
        assert header.startswith("Basic ")
        # base64("test_client_id:test_client_secret")
        import base64
        decoded = base64.b64decode(header.split(" ")[1]).decode()
        assert decoded == "test_client_id:test_client_secret"

    @patch("ebay_oauth.auth.httpx.Client")
    def test_get_access_token_refreshes(self, mock_client_cls, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 7200,
            "token_type": "User Access Token",
        }
        mock_response.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.post.return_value = mock_response
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_http

        token = client.get_access_token()
        assert token == "new_access_token"
        assert client._access_token == "new_access_token"

        # Verify the POST was called with correct params
        mock_http.post.assert_called_once()
        call_kwargs = mock_http.post.call_args
        assert "refresh_token" in call_kwargs.kwargs.get("data", {}).get("grant_type", "")
        assert call_kwargs.kwargs["headers"]["Authorization"].startswith("Basic ")

    @patch("ebay_oauth.auth.httpx.Client")
    def test_get_access_token_uses_cache(self, mock_client_cls, client):
        # Set a cached token that hasn't expired
        client._access_token = "cached_token"
        client._token_expiry = time.time() + 3600

        token = client.get_access_token()
        assert token == "cached_token"
        mock_client_cls.assert_not_called()

    @patch("ebay_oauth.auth.httpx.Client")
    def test_get_access_token_refreshes_when_expired(self, mock_client_cls, client):
        # Set an expired cached token
        client._access_token = "old_token"
        client._token_expiry = time.time() - 100

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "refreshed_token",
            "expires_in": 7200,
        }
        mock_response.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.post.return_value = mock_response
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_http

        token = client.get_access_token()
        assert token == "refreshed_token"

    @patch("ebay_oauth.auth.httpx.Client")
    def test_force_refresh(self, mock_client_cls, client):
        client._access_token = "cached"
        client._token_expiry = time.time() + 9999

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "forced_token",
            "expires_in": 7200,
        }
        mock_response.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.post.return_value = mock_response
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_http

        token = client.force_refresh()
        assert token == "forced_token"
        mock_http.post.assert_called_once()

    @patch("ebay_oauth.auth.httpx.Client")
    def test_no_access_token_in_response(self, mock_client_cls, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_response.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.post.return_value = mock_response
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_http

        with pytest.raises(RuntimeError, match="No access_token"):
            client.get_access_token()


class TestTokenStorage:
    @patch("ebay_oauth.token_storage.keyring")
    def test_store_and_get(self, mock_keyring):
        from ebay_oauth.token_storage import store_credentials, get_credentials

        store_credentials({"refresh_token": "test123"})
        mock_keyring.set_password.assert_called_once()

        mock_keyring.get_password.return_value = '{"refresh_token": "test123"}'
        creds = get_credentials()
        assert creds["refresh_token"] == "test123"

    @patch("ebay_oauth.token_storage.keyring")
    def test_get_returns_none_on_missing(self, mock_keyring):
        from ebay_oauth.token_storage import get_credentials

        mock_keyring.get_password.return_value = None
        assert get_credentials() is None

    @patch("ebay_oauth.token_storage.keyring")
    def test_delete(self, mock_keyring):
        from ebay_oauth.token_storage import delete_credentials

        assert delete_credentials() is True
        mock_keyring.delete_password.assert_called_once()

    @patch("ebay_oauth.token_storage.keyring")
    def test_delete_handles_error(self, mock_keyring):
        from ebay_oauth.token_storage import delete_credentials

        mock_keyring.delete_password.side_effect = Exception("not found")
        assert delete_credentials() is False


class TestCallbackServer:
    def test_find_available_port(self):
        from ebay_oauth.server import _find_available_port
        port = _find_available_port()
        assert 8880 <= port <= 8899

    def test_generate_nonce(self):
        from ebay_oauth.server import _generate_nonce
        nonce = _generate_nonce()
        assert len(nonce) > 20
        # Nonces should be unique
        assert _generate_nonce() != nonce

    def test_start_callback_server(self):
        from ebay_oauth.server import start_callback_server
        port, nonce, server = start_callback_server()
        assert 8880 <= port <= 8899
        assert len(nonce) > 20
        assert server is not None
        server.server_close()
