"""Real loopback HTTP tests; no external service or private data."""
import base64
import http.client
import importlib
import json
import threading
import unittest


class WebTests(unittest.TestCase):
    def setUp(self):
        try:
            self.web = importlib.import_module("importproof.web")
        except ModuleNotFoundError:
            self.fail("The loopback web server has not been implemented")
        self.server = self.web.create_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host = "127.0.0.1:%d" % self.server.server_port

    def tearDown(self):
        if hasattr(self, "server"):
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(5)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=40)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def config(self):
        status, _, body = self.request("GET", "/api/config")
        self.assertEqual(status, 200)
        return json.loads(body)

    def post(self, payload, token=None, extra=None):
        headers = {"Content-Type": "application/json", "X-ImportProof-Token": token or self.config()["token"]}
        headers.update(extra or {})
        return self.request("POST", "/api/compare", json.dumps(payload).encode(), headers)

    def payload(self, before=b"id,value\n1,001\n", after=b"id,value\n1,1\n"):
        return {"before": {"name": "before.csv", "data": base64.b64encode(before).decode()},
                "after": {"name": "after.csv", "data": base64.b64encode(after).decode()}, "options": {"keys": ["id"]}}

    def test_actual_compare_returns_report_and_safe_exports(self):
        status, headers, body = self.post(self.payload())
        self.assertEqual(status, 200, body)
        result = json.loads(body)
        self.assertEqual(result["report"]["verdict"], "CONFIRMED_LOSS")
        self.assertIn("<!doctype html>", result["html"].lower())
        self.assertIn("before", result["csv"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_wrong_host_origin_and_token_cannot_get_or_run_api(self):
        status, _, body = self.request("GET", "/api/config", headers={"Host": "attacker.example"})
        self.assertEqual(status, 403)
        self.assertNotIn("token", json.loads(body))
        status, _, _ = self.request("GET", "/api/config", headers={"Origin": "https://attacker.example"})
        self.assertEqual(status, 403)
        self.assertEqual(self.post(self.payload(), token="wrong")[0], 403)
        self.assertEqual(self.post(self.payload(), extra={"Origin": "https://attacker.example"})[0], 403)
        status, _, _ = self.post(self.payload(), extra={"Origin": "http://" + self.host})
        self.assertEqual(status, 200)

    def test_invalid_base64_and_oversized_upload_are_json_errors(self):
        payload = self.payload()
        payload["before"]["data"] = "not!base64"
        status, _, body = self.post(payload)
        self.assertEqual(status, 400, body)
        self.assertIn("error", json.loads(body))
        oversized = self.payload(before=b"x" * (5 * 1024 * 1024 + 1))
        status, _, body = self.post(oversized)
        self.assertEqual(status, 413, body)
        self.assertIn("error", json.loads(body))

    def test_json_schema_and_unknown_routes_do_not_accept_paths(self):
        for payload in ({}, {"before": {"name": "../secret.csv", "data": ""}, "after": {"name": "a.csv", "data": ""}}, self.payload() | {"options": []}):
            status, _, body = self.post(payload)
            self.assertEqual(status, 400, body)
        status, _, _ = self.request("GET", "/../../pyproject.toml")
        self.assertEqual(status, 404)

    def test_static_assets_are_local_and_security_headers_restrict_network(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"ImportProof", body)
        self.assertIn("default-src 'self'", headers.get("Content-Security-Policy", ""))
        self.assertIn("connect-src 'self'", headers.get("Content-Security-Policy", ""))
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(self.request("GET", "/app.js")[0], 200)
        self.assertEqual(self.request("GET", "/style.css")[0], 200)

    def test_methods_and_protocol_errors_return_json(self):
        for method in ("OPTIONS", "PUT", "DELETE", "PATCH"):
            status, headers, body = self.request(method, "/api/compare")
            self.assertEqual(status, 405)
            self.assertIn("application/json", headers["Content-Type"])
            self.assertIn("error", json.loads(body))
        status, _, body = self.request("POST", "/api/compare", b"{}", {"Content-Type": "application/json"})
        self.assertEqual(status, 403)
        self.assertIn("error", json.loads(body))

    def test_rejected_upload_body_still_receives_json_error(self):
        status, _, body = self.post(self.payload(before=b"x" * (1024 * 1024)), token="wrong")
        self.assertEqual(status, 403)
        self.assertIn("error", json.loads(body))

    def test_non_ascii_session_token_is_rejected_without_server_error(self):
        status, _, body = self.post(self.payload(), token="\xff")
        self.assertEqual(status, 403)
        self.assertIn("error", json.loads(body))

    def test_oversized_request_target_is_a_json_protocol_error(self):
        status, _, body = self.request("GET", "/" + "x" * 66000)
        self.assertEqual(status, 414)
        self.assertIn("error", json.loads(body))

    def test_export_response_limit_returns_error_instead_of_partial_report(self):
        # Each file stays below 5 MiB; evidence repeated across exports exceeds
        # the response cap even though the worker's JSON report is bounded.
        before = b"id,value\n" + b"".join(str(i).encode() + b"," + b"a" * 32000 + b"\n" for i in range(110))
        after = b"id,value\n" + b"".join(str(i).encode() + b"," + b"b" * 32000 + b"\n" for i in range(110))
        status, _, body = self.post(self.payload(before, after))
        self.assertEqual(status, 413, body[:1000])
        value = json.loads(body)
        self.assertIn("error", value)
        self.assertNotIn("report", value)

    def test_request_body_limit_rejects_before_reading_and_tokens_change_per_run(self):
        token = self.config()["token"]
        status, _, body = self.request("POST", "/api/compare", b"", {
            "Content-Type": "application/json", "Content-Length": str(15 * 1024 * 1024 + 1), "X-ImportProof-Token": token})
        self.assertEqual(status, 413)
        self.assertIn("error", json.loads(body))
        second = self.web.create_server(0)
        thread = threading.Thread(target=second.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", second.server_port, timeout=5)
            connection.request("GET", "/api/config")
            other = json.loads(connection.getresponse().read())["token"]
            connection.close()
            self.assertNotEqual(token, other)
        finally:
            second.shutdown()
            second.server_close()
            thread.join(5)


if __name__ == "__main__":
    unittest.main()
