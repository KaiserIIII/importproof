"""Bounded loopback-only HTTP interface. No arbitrary server file access."""
import base64
import binascii
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import socket

from .models import MAX_FILE_BYTES
from .reports import render_csv, render_html

MAX_BODY_BYTES = 15 * 1024 * 1024
MAX_RESPONSE_BYTES = 24 * 1024 * 1024
_STATIC = Path(__file__).with_name("static")


class _LocalServer(HTTPServer):
    # One executing request, bounded kernel backlog: no unbounded request threads.
    request_queue_size = 4
    allow_reuse_address = True

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(10)
        return connection, address


class _Handler(BaseHTTPRequestHandler):
    server_version = "ImportProof"
    sys_version = ""

    def log_message(self, format, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        # BaseHTTPRequestHandler otherwise emits HTML for malformed HTTP/methods.
        self._error(code, message or self.responses.get(code, ("Request failed",))[0])

    def _respond(self, status, body, content_type="application/json; charset=utf-8"):
        self.close_connection = True
        # Closing with an unread upload can turn an HTTP error into a TCP reset
        # on Windows. Discard a bounded, declared body before returning errors.
        if getattr(self, "headers", None) is not None and self.command not in ("GET", "HEAD") and not getattr(self, "_body_read", False):
            self._body_read = True
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if 0 < length <= MAX_BODY_BYTES and not self.headers.get("Transfer-Encoding"):
                    previous_timeout = self.connection.gettimeout()
                    self.connection.settimeout(0.5)
                    try:
                        self.rfile.read(length)
                    finally:
                        self.connection.settimeout(previous_timeout)
            except (ValueError, OSError):
                pass
        if len(body) > MAX_RESPONSE_BYTES:
            status, body, content_type = 413, b'{"error":"Response exceeds 24 MiB; reduce the input or use the CLI."}', "application/json; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status, value):
        self._respond(status, json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"))

    def _error(self, status, message):
        self._json(status, {"error": message})

    def _trusted(self):
        expected_host = f"127.0.0.1:{self.server.server_port}"
        hosts = self.headers.get_all("Host", [])
        origins = self.headers.get_all("Origin", [])
        if hosts != [expected_host] or (origins and origins != [f"http://{expected_host}"]) or self.headers.get("Sec-Fetch-Site") == "cross-site":
            self._error(403, "Host or Origin is not allowed")
            return False
        return True

    def do_GET(self):
        if not self._trusted():
            return
        if self.path == "/api/config":
            self._json(200, {"token": self.server.token, "max_file_bytes": MAX_FILE_BYTES})
            return
        assets = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
        if self.path not in assets:
            self._error(404, "Not found")
            return
        name, content_type = assets[self.path]
        try:
            self._respond(200, (_STATIC / name).read_bytes(), content_type)
        except OSError:
            self._error(500, "Local interface assets are unavailable")

    def do_HEAD(self):
        self.do_GET()

    def do_OPTIONS(self):
        self._error(405, "Method not allowed")

    do_PUT = do_OPTIONS
    do_DELETE = do_OPTIONS
    do_PATCH = do_OPTIONS

    def do_POST(self):
        try:
            self._post()
        except (socket.timeout, TimeoutError):
            self._error(408, "Request timed out")
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _post(self):
        if not self._trusted():
            return
        if self.path != "/api/compare":
            self._error(404, "Not found")
            return
        tokens = self.headers.get_all("X-ImportProof-Token", [])
        if len(tokens) != 1 or not tokens[0].isascii() or not hmac.compare_digest(tokens[0], self.server.token):
            self._error(403, "A valid local session token is required")
            return
        if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
            self._error(400, "A single Content-Length is required; chunked bodies are unsupported")
            return
        try:
            length = int(self.headers["Content-Length"])
        except ValueError:
            self._error(400, "Invalid Content-Length")
            return
        if length < 0 or length > MAX_BODY_BYTES:
            self._error(413, "Request body exceeds 15 MiB")
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self._error(415, "Content-Type must be application/json")
            return
        self._body_read = True
        body = self.rfile.read(length)
        if len(body) != length:
            self._error(400, "Incomplete request body")
            return
        try:
            payload = json.loads(body.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON number")))
            if not isinstance(payload, dict) or set(payload) - {"before", "after", "options"}:
                raise ValueError("Expected before, after and optional options fields")
            options = payload.get("options", {})
            if not isinstance(options, dict):
                raise ValueError("Options must be a JSON object")
            files = []
            for side in ("before", "after"):
                item = payload.get(side)
                if not isinstance(item, dict) or set(item) != {"name", "data"}:
                    raise ValueError(f"{side} must contain name and base64 data")
                name, encoded = item["name"], item["data"]
                if not isinstance(name, str) or not name or len(name) > 255 or any(character in name for character in ("/", "\\", "\x00")) or any(ord(c) < 32 for c in name):
                    raise ValueError("Upload names must be plain filenames, not paths")
                if not isinstance(encoded, str):
                    raise ValueError("Upload data must be a base64 string")
                data = base64.b64decode(encoded, validate=True)
                if len(data) > MAX_FILE_BYTES:
                    self._error(413, "Each file is limited to 5 MiB")
                    return
                files.append((data, name))
            from .worker import audit_bytes
            report = audit_bytes(files[0][0], files[0][1], files[1][0], files[1][1], options)
            self._json(200, {"report": report, "html": render_html(report), "csv": render_csv(report)})
        except (ValueError, UnicodeError, binascii.Error, RecursionError) as error:
            self._error(400, str(error)[:1000] or "Invalid request")
        except Exception:
            self._error(500, "Comparison could not be completed")


def create_server(port: int = 0) -> HTTPServer:
    """Create a server on IPv4 loopback only. Caller owns serve/close lifecycle."""
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("Port must be an integer between 0 and 65535")
    server = _LocalServer(("127.0.0.1", port), _Handler)
    server.token = secrets.token_urlsafe(32)
    return server
