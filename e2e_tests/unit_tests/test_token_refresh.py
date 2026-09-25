"""Exercise the real E2E request helpers with simulated token expiry and HTTP."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError
from httpx import AsyncClient, MockTransport, Response

import helpers as short_helpers
from e2e_tests import helpers
from e2e_tests.resources import deployment, resource, strings
from e2e_tests.token_provider import TokenProvider


class Clock:
    now = 0

    def advance(self):
        self.now += 3601


class ExpiringCredential:
    """Model the SDK returning a cached token until it needs renewal."""

    def __init__(self, clock, scope):
        self.clock = clock
        self.scope = scope
        self.token = None
        self.renewals = 0

    def get_token(self, scope):
        if scope != self.scope:
            raise AssertionError(f"Wrong scope: {scope}")
        if self.token is None or self.token.expires_on <= self.clock.now:
            self.renewals += 1
            self.token = AccessToken(f"{scope}:{self.renewals}", self.clock.now + 3600)
        return self.token


def operation_response(state, status_code=200, endpoint="/api/operations/test"):
    return Response(status_code, headers={"Location": endpoint}, json={
        "operation": {
            "status": state,
            "message": "Test operation",
            "steps": [],
            "resourceId": "test-resource",
            "resourcePath": "/workspaces/test-resource",
        }
    })


class TokenFactoryTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(helpers.cloud, "get_aad_authority_fqdn", return_value="login.example.test"))

    def test_client_credentials_reuse_credential_and_scope(self):
        with patch.multiple(helpers.config, AAD_TENANT_ID="tenant", TEST_ACCOUNT_CLIENT_ID="client", TEST_ACCOUNT_CLIENT_SECRET="dummy-secret"), \
                patch.object(helpers, "ClientSecretCredential") as factory:
            credential = factory.return_value
            credential.get_token.side_effect = [AccessToken("first", 100), AccessToken("renewed", 200)]
            provider = helpers.get_token("api://workspace", verify=True)

            self.assertEqual(helpers.get_auth_header(provider), {"Authorization": "Bearer first"})
            # E2E tests import helpers both with and without the package prefix.
            self.assertEqual(short_helpers.get_auth_header(provider), {"Authorization": "Bearer renewed"})
            factory.assert_called_once_with("tenant", "client", "dummy-secret", connection_verify=True, authority="login.example.test")
            self.assertEqual([call.args for call in credential.get_token.call_args_list], [("api://workspace/.default",)] * 2)

    def test_password_credentials_keep_user_scope_and_tls_setting(self):
        with patch.multiple(helpers.config, AAD_TENANT_ID="tenant", TEST_ACCOUNT_CLIENT_ID="", TEST_ACCOUNT_CLIENT_SECRET="", TEST_APP_ID="app", TEST_USER_NAME="user", TEST_USER_PASSWORD="dummy-password"), \
                patch.object(helpers, "UsernamePasswordCredential") as factory:
            factory.return_value.get_token.return_value = AccessToken("user-token", 100)
            provider = helpers.get_token("api://workspace", verify=False)

            self.assertEqual(helpers.get_auth_header(provider), {"Authorization": "Bearer user-token"})
            factory.assert_called_once_with("app", "user", "dummy-password", connection_verify=False, authority="login.example.test", tenant_id="tenant")
            factory.return_value.get_token.assert_called_once_with("api://workspace/user_impersonation")

    def test_literal_tokens_remain_supported(self):
        self.assertEqual(helpers.get_auth_header("literal-token"), {"Authorization": "Bearer literal-token"})


class PollingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock = Clock()
        self.requests = []
        self.enterContext(patch.object(helpers.config, "TRE_URL", "https://tre.example.test"))

        async def advance_time(_):
            self.clock.advance()

        self.sleep = self.enterContext(patch.object(resource.asyncio, "sleep", new=AsyncMock(side_effect=advance_time)))

    def provider(self, scope):
        return TokenProvider(ExpiringCredential(self.clock, scope), scope)

    def mock_http(self, handler):
        def record(request):
            self.requests.append(request)
            return handler(request)

        client = AsyncClient(transport=MockTransport(record))
        self.enterContext(patch.object(resource, "AsyncClient", return_value=client))

    async def check_post_refresh(self, method, separate_wait_token):
        mutation_token = self.provider("research")
        wait_token = self.provider("review") if separate_wait_token else None
        poll_scope = "review" if separate_wait_token else "research"
        polls = 0

        def handle(request):
            nonlocal polls
            if request.method == method:
                self.assertEqual(request.headers["Authorization"], "Bearer research:1")
                if method == "PATCH":
                    self.assertEqual(request.headers["etag"], '"resource-etag"')
                return operation_response("deploying", 202)
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.path, "/api/operations/test")
            polls += 1
            self.assertEqual(request.headers["Authorization"], f"Bearer {poll_scope}:{polls}")
            terminal = strings.RESOURCE_STATUS_DEPLOYED if method == "POST" else strings.RESOURCE_STATUS_UPDATED
            return operation_response("pipeline_running" if polls == 1 else terminal)

        self.mock_http(handle)
        result = await resource.post_resource(
            {}, "/api/workspaces", mutation_token, True, method=method,
            etag='"resource-etag"', access_token_for_wait=wait_token)

        self.assertEqual(result, ("/workspaces/test-resource", "test-resource"))
        self.assertEqual([r.method for r in self.requests], [method, "GET", "GET"])
        self.sleep.assert_awaited_once_with(30)

    async def test_create_refreshes_during_polling_without_reposting(self):
        await self.check_post_refresh("POST", separate_wait_token=False)

    async def test_update_refreshes_during_polling_without_repatching(self):
        await self.check_post_refresh("PATCH", separate_wait_token=False)

    async def test_airlock_polling_renews_the_separate_workspace_token(self):
        await self.check_post_refresh("POST", separate_wait_token=True)

    async def test_teardown_refreshes_during_both_polls_and_before_delete(self):
        token = self.provider("workspace")
        polls = {"disable": 0, "delete": 0}

        def handle(request):
            if request.method == "PATCH":
                self.assertEqual(request.headers["Authorization"], "Bearer workspace:1")
                self.assertEqual(request.headers["etag"], "*")
                return operation_response("updating", 202, "/api/operations/disable")
            if request.method == "DELETE":
                self.assertEqual(request.headers["Authorization"], "Bearer workspace:3")
                self.assertEqual(request.headers["etag"], "*")
                return operation_response("deleting", endpoint="/api/operations/delete")

            self.assertEqual(request.method, "GET")
            phase = request.url.path.rsplit("/", 1)[-1]
            polls[phase] += 1
            generation = polls[phase] + (2 if phase == "delete" else 0)
            self.assertEqual(request.headers["Authorization"], f"Bearer workspace:{generation}")
            if polls[phase] == 1:
                return operation_response("pipeline_running")
            if phase == "disable":
                # Expire again after disable completes, before DELETE is sent.
                self.clock.advance()
                return operation_response(strings.RESOURCE_STATUS_UPDATED)
            return operation_response(strings.RESOURCE_STATUS_DELETED)

        self.mock_http(handle)
        result = await resource.disable_and_delete_resource("/api/workspaces/test-resource", token, True)

        self.assertEqual(result, "test-resource")
        self.assertEqual([r.method for r in self.requests], ["PATCH", "GET", "GET", "DELETE", "GET", "GET"])
        self.assertEqual(polls, {"disable": 2, "delete": 2})

    async def check_auth_failure(self, teardown):
        def handle(request):
            if request.method in ("POST", "PATCH"):
                return operation_response("pipeline_running", 202)
            return Response(401)

        self.mock_http(handle)
        token = self.provider("workspace")
        with self.assertRaisesRegex(Exception, "Non 200 response in check_deployment"):
            if teardown:
                await resource.disable_and_delete_resource("/api/workspaces/test-resource", token, True)
            else:
                await resource.post_resource({}, "/api/workspaces", token, True)

        self.assertEqual([r.method for r in self.requests], ["PATCH" if teardown else "POST", "GET"])
        self.sleep.assert_not_awaited()

    async def test_persistent_401_fails_without_reposting_or_unbounded_retry(self):
        await self.check_auth_failure(teardown=False)

    async def test_teardown_401_fails_without_deleting_or_unbounded_retry(self):
        await self.check_auth_failure(teardown=True)

    async def test_renewal_failure_propagates_without_reposting(self):
        credential = Mock()

        def get_token(_):
            if self.clock.now:
                raise ClientAuthenticationError("Simulated renewal failure")
            return AccessToken("first", 3600)

        credential.get_token.side_effect = get_token
        self.mock_http(lambda r: operation_response("pipeline_running", 202 if r.method == "POST" else 200))

        with self.assertRaisesRegex(ClientAuthenticationError, "Simulated renewal failure"):
            await resource.post_resource({}, "/api/workspaces", TokenProvider(credential, "workspace"), True)

        self.assertEqual([r.method for r in self.requests], ["POST", "GET"])

    async def test_wait_false_does_not_request_polling_credentials(self):
        unused_credential = Mock()
        self.mock_http(lambda _: operation_response("deploying", 202))
        await resource.post_resource({}, "/api/workspaces", self.provider("research"), True,
                                     wait=False, access_token_for_wait=TokenProvider(unused_credential, "review"))
        unused_credential.get_token.assert_not_called()
        self.assertEqual([r.method for r in self.requests], ["POST"])

    async def test_terminal_deployment_failure_is_still_reported(self):
        self.mock_http(lambda r: operation_response(
            "deploying" if r.method == "POST" else strings.RESOURCE_STATUS_DEPLOYMENT_FAILED,
            202 if r.method == "POST" else 200))
        with self.assertRaises(AssertionError):
            await resource.post_resource({}, "/api/workspaces", self.provider("workspace"), True)
        self.assertEqual([r.method for r in self.requests], ["POST", "GET"])

    async def test_delete_404_remains_a_terminal_success(self):
        async with AsyncClient(transport=MockTransport(lambda _: Response(404))) as client:
            done, state, _, _ = await deployment.delete_done(client, "/api/operations/delete", self.provider("workspace"))
        self.assertTrue(done)
        self.assertEqual(state, strings.RESOURCE_STATUS_DELETED)


if __name__ == "__main__":
    unittest.main()
