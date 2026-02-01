"""Local HTTP callback server for receiving OAuth redirects."""

import secrets
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from threading import Event
from typing import Any

from .config import CALLBACK_PORT_RANGE, CALLBACK_TIMEOUT_SECONDS


def _find_available_port() -> int:
    """Find an available port in the configured range."""
    start, end = CALLBACK_PORT_RANGE
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available port in range {start}-{end}")


def _generate_nonce() -> str:
    """Generate a cryptographic nonce for CSRF protection."""
    return secrets.token_urlsafe(32)


SUCCESS_HTML = """<!DOCTYPE html>
<html>
<head><title>eBay Connected</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }
.container { text-align: center; background: white; padding: 40px; border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
h1 { color: #0654ba; }
.checkmark { font-size: 64px; color: #0654ba; }
</style></head>
<body><div class="container">
<div class="checkmark">&#10003;</div>
<h1>eBay Connected!</h1>
<p>Your credentials have been securely stored.</p>
<p>You can close this window and return to the terminal.</p>
</div></body></html>"""

ERROR_HTML = """<!DOCTYPE html>
<html>
<head><title>Connection Failed</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }
.container { text-align: center; background: white; padding: 40px; border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
h1 { color: #cc0000; }
.error-icon { font-size: 64px; color: #cc0000; }
.details { background: #f5f5f5; padding: 12px; border-radius: 4px; font-family: monospace; }
</style></head>
<body><div class="container">
<div class="error-icon">&#10007;</div>
<h1>Connection Failed</h1>
<div class="details">%s</div>
</div></body></html>"""


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the OAuth callback."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        params = parse_qs(parsed.query)

        # Validate nonce
        received_nonce = params.get("nonce", [None])[0]
        if received_nonce != self.server.expected_nonce:
            self._send_error("Invalid security token (nonce mismatch)")
            self.server.callback_error = "Nonce mismatch"
            self.server.callback_done.set()
            return

        # Check for errors
        error = params.get("error", [None])[0]
        if error:
            desc = params.get("error_description", [error])[0]
            self._send_error(desc)
            self.server.callback_error = desc
            self.server.callback_done.set()
            return

        # Extract tokens
        access_token = params.get("access_token", [None])[0]
        refresh_token = params.get("refresh_token", [None])[0]

        if not refresh_token:
            self._send_error("Missing refresh token in callback")
            self.server.callback_error = "Missing refresh token"
            self.server.callback_done.set()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(SUCCESS_HTML.encode())

        self.server.callback_result = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": params.get("expires_in", [None])[0],
            "refresh_token_expires_in": params.get("refresh_token_expires_in", [None])[0],
        }
        self.server.callback_done.set()

    def _send_error(self, message: str) -> None:
        self.send_response(400)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write((ERROR_HTML % message).encode())

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress default logging
        pass


def start_callback_server() -> tuple[int, str, "HTTPServer"]:
    """Start the local callback server.

    Returns:
        (port, nonce, server) tuple. Call wait_for_callback(server) to block
        until the callback is received.
    """
    port = _find_available_port()
    nonce = _generate_nonce()

    server = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    server.expected_nonce = nonce  # type: ignore[attr-defined]
    server.callback_result = None  # type: ignore[attr-defined]
    server.callback_error = None  # type: ignore[attr-defined]
    server.callback_done = Event()  # type: ignore[attr-defined]

    return port, nonce, server


def wait_for_callback(server: HTTPServer, timeout: int = CALLBACK_TIMEOUT_SECONDS) -> dict:
    """Block until the OAuth callback is received or timeout.

    Args:
        server: The HTTPServer from start_callback_server()
        timeout: Timeout in seconds

    Returns:
        Dict with access_token, refresh_token, expires_in, refresh_token_expires_in

    Raises:
        TimeoutError: If callback not received within timeout
        RuntimeError: If callback contained an error
    """
    server.timeout = 1  # handle_request timeout for polling

    import time
    deadline = time.monotonic() + timeout

    try:
        while not server.callback_done.is_set():
            if time.monotonic() > deadline:
                raise TimeoutError("OAuth callback not received within timeout")
            server.handle_request()
    finally:
        server.server_close()

    if server.callback_error:
        raise RuntimeError(f"OAuth error: {server.callback_error}")

    return server.callback_result
