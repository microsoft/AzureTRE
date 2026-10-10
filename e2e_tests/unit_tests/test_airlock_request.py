"""Exercise Airlock response handling without deploying Azure resources."""

import json
import unittest
from unittest.mock import patch

from httpx import AsyncClient, MockTransport, Response

from e2e_tests import helpers
from e2e_tests.airlock import request


class AirlockRequestTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))

    async def get_response(self, response, expected_status=200):
        client = AsyncClient(transport=MockTransport(lambda _: response))
        with patch.object(request, "AsyncClient", return_value=client):
            return await request.get_request(
                "/api/workspaces/test/requests/test/link", "test-token", True, expected_status
            )

    async def test_expected_plain_text_errors_return_without_json_decoding(self):
        for status, message in (
            (400, "Airlock request is in invalid status: rejected, blocked or failed."),
            (404, "Airlock request does not exist"),
        ):
            with self.subTest(status=status):
                result = await self.get_response(Response(status, text=message), expected_status=status)
                self.assertEqual(result, message)

    async def test_successful_json_response_is_decoded(self):
        payload = {"airlockRequest": {"id": "test-request", "status": "draft"}}
        self.assertEqual(await self.get_response(Response(200, json=payload)), payload)

    async def test_unexpected_status_still_fails(self):
        for actual, expected in ((200, 400), (400, 200), (404, 400), (500, 200)):
            with self.subTest(actual=actual, expected=expected):
                with self.assertRaises(AssertionError):
                    await self.get_response(Response(actual, text="unexpected response"), expected_status=expected)

    async def test_malformed_successful_json_still_fails(self):
        with self.assertRaises(json.JSONDecodeError):
            await self.get_response(Response(200, text="not JSON"))

    async def test_link_response_does_not_log_sas(self):
        payload = {"containerUrl": "https://storage.example.test/container?sig=test-secret-sas"}
        with self.assertLogs(request.LOGGER, level="DEBUG") as logs:
            self.assertEqual(await self.get_response(Response(200, json=payload)), payload)
        self.assertNotIn("test-secret-sas", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
