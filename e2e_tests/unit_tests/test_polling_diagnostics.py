"""Keep useful HTTP failure evidence without exposing response data or credentials."""

import unittest
from unittest.mock import patch

from httpx import AsyncClient, MockTransport, Response

from e2e_tests import helpers
from e2e_tests.resources import deployment, strings


WORKSPACE = "9f293650-29c7-4291-a074-c5c0aaedd7b7"
OPERATION = "2913b8be-2594-4088-8d93-42a296fe69cc"
REQUEST_ID = "05c22c61-9d22-49d7-b333-65b86a0d70dd"
TRACE = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
ENDPOINT = f"/api/workspaces/{WORKSPACE}/operations/{OPERATION}"


class PollingDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))

    async def failure_log(self, response, endpoint=ENDPOINT):
        requests = []

        def handle(request):
            requests.append(request)
            return response

        with self.assertLogs(deployment.LOGGER, level="ERROR") as logs:
            async with AsyncClient(transport=MockTransport(handle)) as client:
                with self.assertRaisesRegex(Exception, "Non 200 response in check_deployment"):
                    await deployment.check_deployment(client, endpoint, "request-token-secret")
        self.assertEqual(len(requests), 1, "An HTTP failure must not trigger a retry")
        return "\n".join(logs.output)

    async def test_records_utc_time_path_status_and_valid_correlation_ids(self):
        log = await self.failure_log(
            Response(
                500,
                content=b"Internal Server Error",
                headers={
                    "content-type": "text/plain; charset=utf-8",
                    "x-ms-request-id": REQUEST_ID,
                    "traceparent": TRACE,
                },
            )
        )
        for value in (ENDPOINT, "500", "GET", "text/plain", REQUEST_ID, TRACE):
            self.assertIn(value, log)
        self.assertRegex(log, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00")
        self.assertIn("body_bytes", log)
        self.assertIn("body_kind", log)

    async def test_excludes_body_query_fragment_credentials_and_arbitrary_headers(self):
        secret = "sensitive-payload-secret"
        log = await self.failure_log(
            Response(
                500,
                json={"error": secret},
                headers={
                    "set-cookie": secret,
                    "authorization": secret,
                    "x-unknown-header": secret,
                    "x-ms-request-id": secret,
                },
            ),
            ENDPOINT + "?sig=query-secret#fragment-secret",
        )
        self.assertIn(ENDPOINT, log)
        for value in (secret, "query-secret", "fragment-secret", "request-token-secret", "tre.example.test"):
            self.assertNotIn(value, log)
        self.assertIn("json_like", log)

    async def test_suppresses_unknown_paths_and_unbounded_header_values(self):
        log = await self.failure_log(
            Response(
                500,
                content=b"body-secret" * 1000,
                headers={
                    "content-type": "secret-media-type" * 1000,
                    "x-ms-correlation-request-id": "a" * 10000,
                    "request-id": "line-one\nline-two",
                    "traceparent": "bad-trace-secret",
                },
            ),
            "/api/operations/path-secret",
        )
        self.assertIn("<redacted>", log)
        for value in ("path-secret", "secret-media-type", "line-one", "line-two", "bad-trace-secret", "body-secret"):
            self.assertNotIn(value, log)
        self.assertLess(len(log), 1200)

    async def test_classifies_response_without_copying_its_content(self):
        for content, content_type, expected in (
            (b"", "", "empty"),
            (b"  <!DOCTYPE html><html>failure</html>", "text/html", "html_like"),
            (b"[not even valid json", "application/json", "json_like"),
            (b"Internal Server Error", "text/plain", "other"),
            (b"\x00\xff", "application/octet-stream", "other"),
        ):
            with self.subTest(expected=expected, content_type=content_type):
                log = await self.failure_log(Response(500, content=content, headers={"content-type": content_type}))
                self.assertIn(expected, log)

    async def test_other_http_errors_still_fail_once(self):
        for code in (400, 401, 403, 429, 503):
            with self.subTest(code=code):
                log = await self.failure_log(Response(code))
                self.assertIn(str(code), log)

    async def test_workspace_service_and_shared_service_operation_paths_are_retained(self):
        for endpoint in (
            f"/api/operations/{OPERATION}",
            f"/api/shared-services/{WORKSPACE}/operations/{OPERATION}",
            f"/api/workspaces/{WORKSPACE}/workspace-services/{WORKSPACE}/operations/{OPERATION}",
            f"/api/workspaces/{WORKSPACE}/workspace-services/{WORKSPACE}/user-resources/{WORKSPACE}/operations/{OPERATION}",
        ):
            with self.subTest(endpoint=endpoint):
                log = await self.failure_log(Response(500), endpoint)
                self.assertIn(endpoint, log)

    async def test_success_and_deletion_keep_the_existing_results(self):
        for response, expected in (
            (Response(200, json={"operation": {"status": "deleting", "message": "waiting", "steps": []}}), "deleting"),
            (Response(404), strings.RESOURCE_STATUS_DELETED),
        ):
            with self.subTest(expected=expected), patch.object(deployment.LOGGER, "error") as log:
                async with AsyncClient(transport=MockTransport(lambda _: response)) as client:
                    state, _, _ = await deployment.check_deployment(client, ENDPOINT, "token")
                self.assertEqual(state, expected)
                log.assert_not_called()
