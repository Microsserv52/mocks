"""HTTP regression tests using only the Python standard library."""

import base64
import hashlib
import hmac
import http.client
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]


def load_mock(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / name / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


class IdentityTests(unittest.TestCase):
    def test_tokens_and_invalid_requests(self):
        mock = load_mock("identity")
        mock.SECRET = b"test-secret"
        with serve(mock.IdentityHandler) as port:
            for payload in ([], None, "text", 1, {"roles": "admin"},
                            *({"ttl_seconds": ttl} for ttl in (None, [], {}, True, "abc", 1.5))):
                with self.subTest(payload=payload):
                    status, _, body = request(port, "POST", "/token", json.dumps(payload))
                    self.assertEqual(status, 400)
                    self.assertEqual(json.loads(body)["code"], "INVALID_REQUEST")
            for body, headers in ((b"\xff", {}), (b"{", {}), (b"", {"Content-Length": "-1"}),
                                  (b"", {"Content-Length": "65537"})):
                self.assertEqual(request(port, "POST", "/token", body, headers)[0], 400)
            for ttl, expected in ((1, 60), (999999, 86400), ("120", 120)):
                status, _, body = request(port, "POST", "/token", json.dumps({
                    "sub": "user", "roles": ["ROLE_ADMIN"], "ttl_seconds": ttl,
                }))
                self.assertEqual(status, 200)
                token = json.loads(body)
                self.assertEqual(token["expires_in"], expected)
                header, payload, signature = token["access_token"].split(".")
                expected_signature = hmac.new(mock.SECRET, f"{header}.{payload}".encode(), hashlib.sha256).digest()
                self.assertEqual(base64.urlsafe_b64decode(signature + "=="), expected_signature)
                claims = json.loads(base64.urlsafe_b64decode(payload + "=="))
                self.assertEqual(claims["sub"], "user")
                self.assertEqual(claims["exp"] - claims["iat"], expected)
            mock.SECRET = b""
            self.assertEqual(request(port, "POST", "/token", "{}")[0], 500)


class StorageTests(unittest.TestCase):
    def test_object_lifecycle_and_invalid_uploads(self):
        mock = load_mock("image-storage")
        with tempfile.TemporaryDirectory() as directory, serve(mock.ImageStorageHandler) as port:
            mock.DATA_DIR = directory
            self.assertEqual(request(port, "PUT", "/upload/photo.png", b"image", {"Content-Type": "image/custom"})[0], 201)
            status, headers, body = request(port, "GET", "/object/photo.png")
            self.assertEqual((status, headers["Content-Type"], body), (200, "image/custom", b"image"))
            self.assertEqual(request(port, "PUT", "/object/photo.png", b"new", {"If-None-Match": "*"})[0], 412)
            for key in ("photo.png.ctype", "photo.png.ctype/child", "%2e%2e/outside", "bad%5ckey"):
                with self.subTest(key=key):
                    self.assertEqual(request(port, "PUT", f"/object/{key}", b"bad")[0], 400)
                    self.assertEqual(request(port, "GET", f"/media/{key}")[0], 404)
            for length, expected in (("-1", 400), ("bad", 400), (str(mock.MAX_OBJECT_BYTES + 1), 413)):
                self.assertEqual(request(port, "PUT", "/object/invalid", b"", {"Content-Length": length})[0], expected)
            self.assertFalse((Path(directory) / "invalid").exists())
            self.assertEqual(request(port, "PUT", "/object/photo.png", b"replacement")[0], 201)
            status, headers, body = request(port, "GET", "/media/photo.png")
            self.assertEqual((status, headers["Content-Type"], body), (200, "image/png", b"replacement"))
            self.assertEqual(request(port, "DELETE", "/object/photo.png")[0], 204)
            self.assertEqual(request(port, "GET", "/object/photo.png")[0], 404)

    def test_truncated_upload_does_not_replace_existing_object(self):
        mock = load_mock("image-storage")
        with tempfile.TemporaryDirectory() as directory, serve(mock.ImageStorageHandler) as port:
            mock.DATA_DIR = directory
            target = Path(directory) / "image"
            target.write_bytes(b"original")
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            try:
                connection.request("PUT", "/object/image", b"short", {"Content-Length": "10"})
                connection.sock.shutdown(socket.SHUT_WR)
                response = connection.getresponse()
                self.assertEqual(response.status, 400)
                response.read()
                self.assertEqual(target.read_bytes(), b"original")
            finally:
                connection.close()


class ProviderTests(unittest.TestCase):
    def test_provider_contract_and_modes(self):
        mock = load_mock("exchange-provider")
        mock.REQUIRED_KEY = "test-key"
        mock.MODE = "ok"
        headers = {"Authorization": "Bearer test-key"}
        with serve(mock.ProviderHandler) as port:
            self.assertEqual(request(port, "GET", "/health")[0], 200)
            self.assertEqual(request(port, "GET", "/latest")[0], 401)
            for path in ("/latest", "/v1/latest", "/latest.json"):
                status, _, body = request(port, "GET", path + "?base=USD&symbols=EUR,BRL", headers=headers)
                payload = json.loads(body)
                self.assertEqual(status, 200)
                self.assertEqual(payload["date"], "2026-01-01T00:00:00Z")
                self.assertEqual(payload["rates"]["EUR"], {"bid": 0.815556, "ask": 0.819644})
            for mode, expected in (("error", 503), ("rate_limit", 429), ("unsupported", 400), ("malformed", 200)):
                self.assertEqual(request(port, "POST", f"/control?mode={mode}")[0], 200)
                status, response_headers, body = request(port, "GET", "/latest", headers=headers)
                self.assertEqual(status, expected)
                if mode == "rate_limit":
                    self.assertEqual(response_headers["Retry-After"], "2")
                if mode == "malformed":
                    self.assertEqual(body, b"not-json")
            self.assertEqual(request(port, "POST", "/control?mode=invalid")[0], 400)
            request(port, "POST", "/control?mode=ok")
            for query in ("base=XXX", "symbols=XXX"):
                self.assertEqual(request(port, "GET", "/latest?" + query, headers=headers)[0], 400)


class ProductionGuardTests(unittest.TestCase):
    def test_all_entrypoints_refuse_production(self):
        for name in ("identity", "image-storage", "exchange-provider"):
            for variable in ("ENV", "APP_ENV"):
                for value in ("prod", " Production "):
                    with self.subTest(mock=name, variable=variable, value=value):
                        env = {**os.environ, "ENV": "test", "APP_ENV": "test", variable: value}
                        result = subprocess.run([sys.executable, str(ROOT / name / "server.py")], env=env, capture_output=True, text=True, timeout=3)
                        self.assertEqual(result.returncode, 1)
                        self.assertIn("refusing to start:", result.stderr)


if __name__ == "__main__":
    unittest.main()
