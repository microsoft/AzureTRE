"""Exercise OHDSI ownership, pipeline completion and bounded cleanup failures."""

import asyncio
from builtins import ExceptionGroup
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from e2e_tests.resources import ohdsi_lifecycle as lc

WORKSPACE = "11111111-1111-4111-8111-111111111111"
SERVICE = "22222222-2222-4222-8222-222222222222"
OPERATION = "33333333-3333-4333-8333-333333333333"
OLD = "44444444-4444-4444-8444-444444444444"
ENDPOINT = f"/api/workspaces/{WORKSPACE}/workspace-services"
PATH = ENDPOINT.removeprefix("/api") + "/" + SERVICE
PAYLOAD = {
    "templateName": "tre-workspace-service-ohdsi",
    "properties": {"display_name": "unique name", "description": "owned resource", "configure_data_source": False},
}


def response(body=None, code=200):
    return SimpleNamespace(status_code=code, json=lambda: body)


def owner():
    return lc.OwnedResource(
        PATH, SERVICE, "workspaceService", PAYLOAD["templateName"], "unique name", "owned resource", WORKSPACE
    )


def record(state="deployed", **properties):
    return {
        "id": SERVICE,
        "templateName": PAYLOAD["templateName"],
        "properties": PAYLOAD["properties"] | properties,
        "deploymentStatus": state,
        "_etag": "tag",
    }


def operations(state="deployed", identifier=OPERATION):
    return response({"operations": [{"id": identifier, "status": state}]})


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        now = asyncio.get_running_loop().time()
        self.resources = lc.OHDSIResources(True, now + 5, now + 10)
        self.client = AsyncMock()
        self.client.__aenter__.return_value = self.client
        self.client.post.return_value = response(
            {"operation": {"id": OPERATION, "resourceId": SERVICE, "resourcePath": PATH}}, 202
        )
        self.enterContext(patch.object(lc, "AsyncClient", return_value=self.client))
        self.token = self.enterContext(patch.object(lc, "get_workspace_owner_token", AsyncMock(return_value="owner")))
        self.admin = self.enterContext(patch.object(lc, "get_admin_token", AsyncMock(return_value="admin")))
        self.evidence = self.enterContext(patch.object(lc, "record_resource"))
        self.enterContext(patch.object(lc, "record_operation"))
        self.enterContext(patch.object(lc, "get_full_endpoint", side_effect=lambda p: "https://tre" + p))
        self.remove = self.enterContext(patch.object(lc, "disable_and_delete_resource", AsyncMock()))

    async def test_accepted_resource_is_owned_before_client_exit_cancellation(self):
        self.client.__aexit__.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.resources.create(PAYLOAD, ENDPOINT, WORKSPACE)
        self.assertEqual(self.resources.owned[0].path, PATH)
        self.evidence.assert_called_once()
        self.token.assert_awaited_once_with(WORKSPACE, True)
        self.admin.assert_not_awaited()

    async def test_evidence_error_does_not_lose_accepted_identity(self):
        self.evidence.side_effect = OSError("disk full")
        with self.assertRaises(OSError):
            await self.resources.create(PAYLOAD, ENDPOINT, WORKSPACE)
        self.assertEqual(self.resources.owned[0].identifier, SERVICE)

    async def test_external_source_or_wrong_parent_is_rejected_before_post(self):
        for properties in ({"configure_data_source": True}, {"data_source_config": {}}, {"data_source_daimons": {}}):
            with self.assertRaises(ValueError):
                await self.resources.create(
                    PAYLOAD | {"properties": PAYLOAD["properties"] | properties}, ENDPOINT, WORKSPACE
                )
        with self.assertRaises(ValueError):
            await self.resources.create(PAYLOAD, "/api/shared-services", WORKSPACE)
        self.client.post.assert_not_awaited()

    async def test_failed_pipeline_remains_owned(self):
        with patch.object(
            self.resources, "wait_terminal", AsyncMock(return_value=(record(), [{"status": "pipeline_failed"}]))
        ):
            with self.assertRaisesRegex(RuntimeError, "pipeline"):
                await self.resources.create(PAYLOAD, ENDPOINT, WORKSPACE)
        self.assertEqual(self.resources.owned[0].path, PATH)

    async def test_wait_requires_current_operation_and_terminal_pipeline(self):
        self.client.get.side_effect = [
            response({"workspaceService": record()}),
            operations(identifier=OLD),
            response({"workspaceService": record()}),
            operations("pipeline_running"),
            response({"workspaceService": record()}),
            operations("pipeline_succeeded"),
        ]
        with patch.object(lc.asyncio, "sleep", AsyncMock()) as sleep:
            await self.resources.wait_terminal(owner(), operation_id=OPERATION)
        self.assertEqual(sleep.await_count, 2)

    async def test_ownership_change_prevents_deletion(self):
        self.resources.owned = [owner()]
        self.client.get.return_value = response({"workspaceService": record(description="different owner")})
        errors = await self.resources.close()
        self.assertEqual(len(errors), 1)
        self.remove.assert_not_awaited()

    async def test_reverse_cleanup_reserves_parent_after_child(self):
        workspace = lc.OwnedResource(
            "/workspaces/" + WORKSPACE, WORKSPACE, "workspace", "tre-workspace-base", "test", "owned", None
        )
        self.resources.owned = [workspace, owner()]
        with patch.object(self.resources, "remove", AsyncMock()) as remove:
            self.assertEqual(await self.resources.close(), [])
        self.assertEqual([c.args[0].identifier for c in remove.await_args_list], [SERVICE, WORKSPACE])

    async def test_child_failure_retains_parent_and_reports_both(self):
        workspace = lc.OwnedResource(
            "/workspaces/" + WORKSPACE, WORKSPACE, "workspace", "tre-workspace-base", "test", "owned", None
        )
        self.resources.owned = [workspace, owner()]
        with patch.object(self.resources, "remove", AsyncMock(side_effect=RuntimeError("delete failed"))) as remove:
            errors = await self.resources.close()
        self.assertEqual(remove.await_count, 1)
        self.assertEqual(len(errors), 2)
        self.assertIn("retained", str(errors[1]))

    async def test_absent_resource_still_checks_azure_and_pipeline_cleanup(self):
        resource = owner()
        resource.after_remove = AsyncMock()
        with patch.object(self.resources, "wait_terminal", AsyncMock(return_value=None)):
            await self.resources.remove(resource)
        self.remove.assert_not_awaited()
        resource.after_remove.assert_awaited_once_with(PATH, SERVICE)

    async def test_same_version_upgrade_waits_for_returned_operation(self):
        self.client.patch.return_value = response(
            {"operation": {"id": OPERATION, "resourceId": SERVICE, "resourcePath": PATH}}, 202
        )
        wait = AsyncMock(
            side_effect=[
                (record(), []),
                (record("updated", overview="new"), [{"id": OPERATION, "status": "pipeline_succeeded"}]),
            ]
        )
        with patch.object(self.resources, "wait_terminal", wait):
            await self.resources.upgrade(owner(), "new")
        self.assertEqual(wait.await_args.kwargs, {"operation_id": OPERATION})
        self.assertEqual(self.client.patch.call_args.kwargs["headers"]["etag"], "tag")
        self.assertEqual(self.client.patch.call_args.kwargs["json"], {"properties": {"overview": "new"}})

    async def test_deadline_rejects_nonfinite_or_exhausted_budget(self):
        for value in ("nan", "inf", "0"):
            with patch.dict(os.environ, OHDSI_VALIDATION_DEADLINE=value):
                with self.assertRaises((ValueError, TimeoutError)):
                    lc.lifecycle_deadlines()

    async def test_cleanup_failure_fails_an_otherwise_successful_case(self):
        now = asyncio.get_running_loop().time()
        with (
            patch.object(lc, "lifecycle_deadlines", return_value=(now + 2, now + 3)),
            patch.object(lc.OHDSIResources, "close", AsyncMock(return_value=[RuntimeError("cleanup failed")])),
        ):
            with self.assertRaises(ExceptionGroup):
                async with lc.ohdsi_lifecycle(True):
                    pass

    async def test_cancellation_waits_for_cleanup(self):
        started = asyncio.Event()
        release = asyncio.Event()
        done = Mock()

        async def close():
            started.set()
            await release.wait()
            done()
            return []

        async def run():
            async with lc.ohdsi_lifecycle(True):
                pass

        with (
            patch.object(lc.OHDSIResources, "close", side_effect=close),
            patch.dict(os.environ, OHDSI_VALIDATION_DEADLINE=""),
        ):
            task = asyncio.create_task(run())
            await started.wait()
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        done.assert_called_once()
