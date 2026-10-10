"""Exercise Airlock response handling without deploying Azure resources."""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, MockTransport, Response
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError, HttpResponseError

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


class DraftDeletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncMock()
        self.context = MagicMock()
        self.context.__aenter__ = AsyncMock(return_value=self.client)
        self.context.__aexit__ = AsyncMock(return_value=False)
        self.factory = self.enterContext(
            patch.object(request.AsyncBlobClient, "from_blob_url", return_value=self.context)
        )
        self.sas = "https://storage.example.test/draft?sig=private-sas"

    def missing(self, code="ContainerNotFound"):
        error = ResourceNotFoundError("Not found")
        error.error_code = code
        return error

    async def test_transient_writes_are_retried_until_container_not_found(self):
        self.client.upload_blob.side_effect = [{"etag": "written"}, self.missing()]
        await request.wait_for_draft_container_deletion(self.sas, interval=0)
        self.assertEqual(self.client.upload_blob.await_count, 2)
        self.assertTrue(self.client.upload_blob.call_args.kwargs["overwrite"])
        self.assertIn("/draft/revocation-probe-", self.factory.call_args.args[0])

    async def test_container_being_deleted_is_retried_and_not_accepted_as_complete(self):
        error = ResourceExistsError("Deleting")
        error.error_code = "ContainerBeingDeleted"
        self.client.upload_blob.side_effect = [error, self.missing()]
        await request.wait_for_draft_container_deletion(self.sas, interval=0)
        self.assertEqual(self.client.upload_blob.await_count, 2)

    async def test_writes_that_continue_past_deadline_fail(self):
        self.client.upload_blob.return_value = {"etag": "still writable"}
        with self.assertRaisesRegex(AssertionError, "not confirmed within"):
            await request.wait_for_draft_container_deletion(self.sas, timeout=0.01, interval=0.001)

    async def test_conflict_authentication_and_wrong_not_found_errors_fail(self):
        for error in (
            ResourceExistsError("BlobAlreadyExists"),
            HttpResponseError("Forbidden"),
            self.missing("BlobNotFound"),
        ):
            with self.subTest(error=error):
                self.client.upload_blob.side_effect = error
                with self.assertRaises(type(error)):
                    await request.wait_for_draft_container_deletion(self.sas, interval=0)

    async def test_probe_names_are_distinct_and_client_closes(self):
        self.client.upload_blob.side_effect = self.missing()
        await request.wait_for_draft_container_deletion(self.sas)
        first = self.factory.call_args.args[0]
        await request.wait_for_draft_container_deletion(self.sas)
        self.assertNotEqual(first, self.factory.call_args.args[0])
        self.assertEqual(self.context.__aexit__.await_count, 2)


if __name__ == "__main__":
    unittest.main()
