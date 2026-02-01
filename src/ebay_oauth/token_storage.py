"""OS keychain storage for eBay OAuth credentials via keyring."""

import json
import keyring
from .config import KEYRING_SERVICE, KEYRING_ACCOUNT


def store_credentials(credentials: dict) -> None:
    """Store OAuth credentials in the OS keychain."""
    keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, json.dumps(credentials))


def get_credentials() -> dict | None:
    """Retrieve OAuth credentials from the OS keychain."""
    try:
        data = keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
        return json.loads(data) if data else None
    except Exception:
        return None


def delete_credentials() -> bool:
    """Delete OAuth credentials from the OS keychain."""
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
        return True
    except Exception:
        return False


def has_credentials() -> bool:
    """Check if OAuth credentials exist in the OS keychain."""
    return get_credentials() is not None
