"""Check the user resource action helper and the VM state readers."""

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from httpx import Response

from e2e_tests.resources import strings
from e2e_tests.resources import vm_actions as actions

VM_ID = "/subscriptions/sub/resourceGroups/rg-tretest-ws-abcd/providers/Microsoft.Compute/virtualMachines/linuxvm1234"
VAULT_ID = "/subscriptions/sub/resourceGroups/rg-tretest-ws-abcd/providers/Microsoft.KeyVault/vaults/kv-tretest-ws-abcd"
PATH = "/workspaces/ws/workspace-services/svc/user-resources/vm"


class ActionTests(unittest.IsolatedAsyncioTestCase):
    async def test_action_success_and_failure_are_terminal(self):
        for state, done in (
            (strings.RESOURCE_ACTION_STATUS_SUCCEEDED, True),
            (strings.RESOURCE_ACTION_STATUS_FAILED, True),
            (strings.RESOURCE_ACTION_STATUS_INVOKING, False),
            (strings.RESOURCE_STATUS_DEPLOYED, False),
        ):
            with (
                self.subTest(state=state),
                patch.object(actions, "check_deployment", AsyncMock(return_value=(state, "", []))),
            ):
                self.assertEqual((await actions.action_done(None, "/op", "token"))[:2], (done, state))

    async def test_invoke_waits_for_the_action_and_rejects_another_resource(self):
        def response(path):
            return Response(
                202,
                json={"operation": {"id": "op", "resourcePath": path, "resourceId": "vm"}},
                headers={"Location": "/api/op"},
            )

        for path, error in ((PATH, None), ("/workspaces/ws/other", ValueError)):
            post = AsyncMock(return_value=response(path))
            client = SimpleNamespace(post=post)
            client_context = AsyncMock()
            client_context.__aenter__.return_value = client
            with (
                self.subTest(path=path),
                patch.object(actions, "AsyncClient", return_value=client_context),
                patch.object(actions, "record_resource"),
                patch.object(actions, "wait_for", AsyncMock()) as wait,
            ):
                if error:
                    with self.assertRaises(error):
                        await actions.invoke_action(PATH, "stop", "token", True)
                    wait.assert_not_awaited()
                else:
                    await actions.invoke_action(PATH, "stop", "token", True)
                    self.assertEqual(post.await_args.kwargs["params"], {"action": "stop"})
                    self.assertTrue(post.await_args.args[0].endswith(f"/api{PATH}/invoke-action"))
                    self.assertEqual(wait.await_args.args[2], "/api/op")
                    self.assertEqual(wait.await_args.args[4], [strings.RESOURCE_ACTION_STATUS_FAILED])

    async def test_power_state_needs_exactly_one_value(self):
        view = {"statuses": [{"code": "ProvisioningState/succeeded"}, {"code": "PowerState/deallocated"}]}
        arm = SimpleNamespace(request=AsyncMock(return_value=view))
        self.assertEqual(await actions.power_state(arm, VM_ID), "PowerState/deallocated")
        self.assertEqual(arm.request.await_args.args[1], VM_ID + "/instanceView")
        arm.request = AsyncMock(return_value={"statuses": [{"code": "ProvisioningState/succeeded"}]})
        with self.assertRaises(AssertionError):
            await actions.power_state(arm, VM_ID)

    async def test_secret_version_comes_from_arm_metadata(self):
        secret = {"properties": {"secretUriWithVersion": "https://kv.vault.azure.net/secrets/name/abc123"}}
        arm = SimpleNamespace(request=AsyncMock(return_value=secret))
        self.assertEqual(await actions.secret_version(arm, VAULT_ID, "linuxvm1234-admin-credentials"), "abc123")
        self.assertEqual(arm.request.await_args.args[1], VAULT_ID + "/secrets/linuxvm1234-admin-credentials")
