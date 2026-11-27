"""Check the SQL probe's evidence, ownership and recovery boundaries."""

from copy import deepcopy
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from httpx import AsyncClient, MockTransport, Response
from jsonschema import validate

from api_app.services.schema_service import enrich_user_resource_template, enrich_workspace_service_template
from e2e_tests import test_azuresql as sql
from e2e_tests.resources import sql_probe as probe
from e2e_tests.resources import sql_lifecycle as lifecycle


ROOT = Path(__file__).resolve().parents[2]
GROUP = "/subscriptions/sub/resourceGroups/rg-tretest-ws-abcd"
VM_ID = f"{GROUP}/providers/Microsoft.Compute/virtualMachines/windowsvm1234"


def result(**overrides):
    evidence = {"phase": "read", "probe": "abc", "sku": "S2", "row_count": 1, "private_dns": True, **overrides}
    return {
        "properties": {
            "provisioningState": "Succeeded",
            "instanceView": {
                "executionState": "Succeeded",
                "exitCode": 0,
                "output": "SQL_PROBE_RESULT=" + json.dumps(evidence),
            },
        }
    }


class ProbeEvidenceTests(unittest.TestCase):
    def test_success_requires_expected_persisted_data_and_sku(self):
        self.assertTrue(probe.probe_result(result(), "read", "abc", "S2"))
        for change in ({"phase": "write"}, {"probe": "other"}, {"sku": "S1"}, {"row_count": 0}, {"private_dns": False}):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                probe.probe_result(result(**change), "read", "abc", "S2")

    def test_provisioning_success_does_not_prove_command_success(self):
        resource = result()
        resource["properties"]["instanceView"] = {}
        self.assertFalse(probe.probe_result(resource, "read", "abc", "S2"))
        for state, code in (("Failed", 1), ("TimedOut", -1), ("Succeeded", 1)):
            resource["properties"]["instanceView"] = {"executionState": state, "exitCode": code}
            with self.subTest(state=state), self.assertRaises(AssertionError):
                probe.probe_result(resource, "read", "abc", "S2")

    def test_vm_must_belong_to_this_test_workspace_and_user_resource(self):
        vm = {
            "id": VM_ID,
            "tags": {
                "tre_id": "tretest",
                "tre_workspace_id": "ws-abcd",
                "tre_workspace_service_id": "guac",
                "tre_user_resource_id": "vm",
            },
            "identity": {"principalId": "principal"},
        }
        args = (VM_ID, "sub", "tretest", "ws-abcd", "guac", "vm")
        self.assertEqual(probe.validate_vm(vm, *args), GROUP)
        for tag in vm["tags"]:
            changed = deepcopy(vm)
            changed["tags"][tag] = "unrelated"
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                probe.validate_vm(changed, *args)
        with self.assertRaises(ValueError):
            probe.validate_vm(vm, VM_ID, "another-subscription", *args[2:])

    def test_payloads_match_enriched_api_schemas(self):
        cases = (
            (sql.SQL_PAYLOAD, "azuresql", enrich_workspace_service_template),
            (sql.VM_PAYLOAD, "guacamole/user_resources/guacamole-azure-windowsvm", enrich_user_resource_template),
        )
        for payload, folder, enrich in cases:
            with self.subTest(bundle=payload["templateName"]):
                schema = json.loads(
                    (ROOT / "templates/workspace_services" / folder / "template_schema.json").read_text()
                )
                validate(payload["properties"], enrich(SimpleNamespace(model_dump=lambda **_: schema)))
        self.assertFalse(any(v for k, v in sql.VM_PAYLOAD["properties"].items() if k.startswith("install_")))

    def test_oidc_bearer_is_never_sent_to_an_untrusted_endpoint(self):
        with patch.dict(os.environ, {"ACTIONS_ID_TOKEN_REQUEST_URL": "https://example.test/token"}):
            with patch.object(probe.requests, "get") as get, self.assertRaises(ValueError):
                probe.github_assertion()
            get.assert_not_called()

    def test_oidc_request_refreshes_assertion_and_disallows_redirects(self):
        environment = {
            "ACTIONS_ID_TOKEN_REQUEST_URL": "https://test.actions.githubusercontent.com/token?job=1",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "request-token",
        }
        response = Mock(status_code=200)
        response.json.return_value = {"value": "assertion"}
        with patch.dict(os.environ, environment), patch.object(probe.requests, "get", return_value=response) as get:
            self.assertEqual(probe.github_assertion(), "assertion")
            self.assertEqual(probe.github_assertion(), "assertion")
        self.assertEqual(get.call_count, 2)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertEqual(get.call_args.kwargs["params"], {"audience": "api://AzureADTokenExchange"})


class ProbeRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_the_temporary_secret_scoped_assignment_is_deleted(self):
        arm = SimpleNamespace(request=AsyncMock(return_value={}), delete=AsyncMock())
        vault = f"{GROUP}/providers/Microsoft.KeyVault/vaults/kv-test"

        async def failing_query():
            async with probe.secret_access(arm, vault, "sql-password", "principal", "sub"):
                raise RuntimeError("query failed")

        with self.assertRaisesRegex(RuntimeError, "query failed"):
            await failing_query()
        call = arm.request.call_args
        assignment = call.args[1]
        self.assertTrue(
            assignment.startswith(vault + "/secrets/sql-password/providers/Microsoft.Authorization/roleAssignments/")
        )
        self.assertEqual(call.kwargs["body"]["properties"]["principalId"], "principal")
        self.assertTrue(call.kwargs["body"]["properties"]["roleDefinitionId"].endswith(probe.SECRETS_USER))
        arm.delete.assert_awaited_once_with(assignment, probe.ROLE_API)

    async def test_assignment_is_cleaned_if_create_response_is_lost(self):
        arm = SimpleNamespace(request=AsyncMock(side_effect=TimeoutError("response lost")), delete=AsyncMock())
        with self.assertRaises(TimeoutError):
            async with probe.secret_access(arm, GROUP + "/vault", "secret", "principal", "sub"):
                self.fail("Creation should fail")
        arm.delete.assert_awaited_once()

    async def test_failed_command_is_removed_and_never_counts_as_pass(self):
        failed = {"properties": {"instanceView": {"executionState": "Failed", "exitCode": 1}}}
        arm = SimpleNamespace(request=AsyncMock(side_effect=[{}, failed]), delete=AsyncMock())
        with self.assertRaises(AssertionError):
            await probe.run_probe(
                arm,
                VM_ID,
                "switzerlandnorth",
                server="sql.database.windows.net",
                vault_name="kv-test",
                secret_name="sql-password",
                probe_id="abc",
                phase="read",
                expected_sku="S2",
            )
        command = arm.request.call_args_list[0].args[1]
        arm.delete.assert_awaited_once_with(command, probe.COMPUTE_API)
        payload = arm.request.call_args_list[0].kwargs["body"]
        self.assertFalse(any("password" in p["name"].lower() for p in payload["properties"]["parameters"]))

    async def test_arm_deletion_waits_until_resource_is_gone(self):
        calls = []

        def handle(request):
            calls.append(request.method)
            return Response(202) if request.method == "DELETE" else Response(404)

        credential = Mock()
        credential.get_token.return_value = SimpleNamespace(token="offline")
        async with AsyncClient(transport=MockTransport(handle)) as client:
            await probe.ArmClient(client, credential).delete(VM_ID + "/runCommands/probe", probe.COMPUTE_API)
        self.assertEqual(calls, ["DELETE", "GET"])

    async def test_cleanup_waits_for_active_update_before_disable(self):
        events = []

        async def get(*_):
            events.append("poll")
            return {"operations": [{"status": "updating" if len(events) == 1 else "updating_failed"}]}

        async def delete(*_, **__):
            events.append("delete")

        async def timed_out_update():
            async with lifecycle.sql_lifecycle(True) as owned:
                await owned.create({}, "/services", "token")
                raise TimeoutError("update")

        with (
            patch.object(lifecycle, "post_resource", AsyncMock(return_value=("/sql", "id"))),
            patch.object(lifecycle, "get_resource", side_effect=get),
            patch.object(lifecycle, "disable_and_delete_resource", side_effect=delete),
            patch.object(sql.asyncio, "sleep", AsyncMock()),
        ):
            with self.assertRaisesRegex(TimeoutError, "update"):
                await timed_out_update()
        self.assertEqual(events, ["poll", "poll", "delete"])

    async def test_cleanup_failure_preserves_original_query_error(self):
        async def failing_query():
            async with lifecycle.sql_lifecycle(True) as owned:
                await owned.create({}, "/services", "token")
                raise ValueError("query")

        with (
            patch.object(lifecycle, "post_resource", AsyncMock(return_value=("/sql", "id"))),
            patch.object(lifecycle, "get_resource", AsyncMock(return_value={"operations": []})),
            patch.object(lifecycle, "disable_and_delete_resource", AsyncMock(side_effect=RuntimeError("cleanup"))),
        ):
            with self.assertRaisesRegex(ValueError, "query") as raised:
                await failing_query()
        self.assertIn("cleanup", raised.exception.__notes__[0])

    async def test_work_deadline_during_role_revocation_preserves_query_failure_and_waits(self):
        events = []

        async def delete(*args):
            events.append("revoke start")
            await asyncio.sleep(0.1)
            events.append("revoke done")

        async def delete_vm():
            events.append("vm delete")

        arm = SimpleNamespace(request=AsyncMock(), delete=delete)
        with (
            patch.object(lifecycle, "LIFECYCLE_SECONDS", 0.5),
            patch.object(lifecycle, "CLEANUP_RESERVE_SECONDS", 0.45),
            patch.dict(os.environ, SQL_VALIDATION_DEADLINE=""),
        ):
            with self.assertRaisesRegex(RuntimeError, "query failed"):
                async with lifecycle.sql_lifecycle(True) as owned:
                    owned.own("vm", delete_vm)
                    async with probe.secret_access(arm, GROUP + "/vault", "secret", "principal", "sub"):
                        raise RuntimeError("query failed")
        self.assertEqual(events, ["revoke start", "revoke done", "vm delete"])

    async def test_repeated_cancellation_waits_for_command_removal(self):
        started = asyncio.Event()
        removed = asyncio.Event()

        async def delete(*args):
            started.set()
            await asyncio.sleep(0.05)
            removed.set()

        arm = SimpleNamespace(request=AsyncMock(side_effect=RuntimeError("command failed")), delete=delete)
        task = asyncio.create_task(
            probe.run_probe(
                arm,
                VM_ID,
                "switzerlandnorth",
                server="sql.database.windows.net",
                vault_name="kv-test",
                secret_name="secret",
                probe_id="abc",
                phase="read",
                expected_sku="S2",
            )
        )
        await started.wait()
        task.cancel()
        await asyncio.sleep(0.01)
        task.cancel()
        with self.assertRaisesRegex(RuntimeError, "command failed"):
            await task
        self.assertTrue(removed.is_set())

    async def test_work_deadline_during_successful_command_cleanup_still_waits(self):
        events = []

        async def delete(*args):
            events.append("command delete start")
            await asyncio.sleep(0.1)
            events.append("command delete done")

        arm = SimpleNamespace(request=AsyncMock(side_effect=[{}, result()]), delete=delete)
        with (
            patch.object(lifecycle, "LIFECYCLE_SECONDS", 0.5),
            patch.object(lifecycle, "CLEANUP_RESERVE_SECONDS", 0.45),
            patch.dict(os.environ, SQL_VALIDATION_DEADLINE=""),
        ):
            with self.assertRaises(TimeoutError):
                async with lifecycle.sql_lifecycle(True):
                    await probe.run_probe(
                        arm,
                        VM_ID,
                        "switzerlandnorth",
                        server="sql.database.windows.net",
                        vault_name="kv-test",
                        secret_name="secret",
                        probe_id="abc",
                        phase="read",
                        expected_sku="S2",
                    )
        self.assertEqual(events, ["command delete start", "command delete done"])
