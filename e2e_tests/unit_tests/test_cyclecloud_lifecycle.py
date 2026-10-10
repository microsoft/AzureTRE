"""Exercise accepted ownership, pipeline waits, deadlines and cleanup failures."""

import asyncio
from builtins import ExceptionGroup
from copy import deepcopy
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from e2e_tests.resources import cyclecloud_lifecycle as lc
from e2e_tests import test_cyclecloud as case

SERVICE = "22222222-2222-4222-8222-222222222222"
OPERATION = "33333333-3333-4333-8333-333333333333"
OLD_OPERATION = "44444444-4444-4444-8444-444444444444"
PATH = f"/shared-services/{SERVICE}"
PAYLOAD = {"templateName": lc.TEMPLATE, "properties": {"display_name": "unique test", "description": "owned test"}}


def response(body=None, code=200):
    return SimpleNamespace(status_code=code, json=lambda: body)


def accepted(**changes):
    return response({"operation": {"id": OPERATION, "resourceId": SERVICE, "resourcePath": PATH, **changes}}, 202)


def resource(state="deployed", **properties):
    return {
        "id": SERVICE,
        "templateName": lc.TEMPLATE,
        "deploymentStatus": state,
        "_etag": "etag",
        "properties": PAYLOAD["properties"] | properties,
    }


def operations(state="deployed", identifier=OPERATION):
    return response({"operations": [{"id": identifier, "status": state}]})


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.before, self.after = AsyncMock(), AsyncMock()
        self.service = lc.CycleCloudService(
            True, asyncio.get_running_loop().time() + 2, deepcopy(PAYLOAD), self.before, self.after
        )
        self.client = AsyncMock()
        self.client.__aenter__.return_value = self.client
        self.client.post.return_value = accepted()
        self.enterContext(patch.object(lc, "AsyncClient", return_value=self.client))
        self.enterContext(patch.object(lc, "get_admin_token", AsyncMock(return_value="token")))
        self.evidence = self.enterContext(patch.object(lc, "record_resource"))
        self.enterContext(patch.object(lc, "record_operation"))
        self.enterContext(patch.object(lc, "get_full_endpoint", side_effect=lambda v: "https://tre" + v))
        self.remove = self.enterContext(patch.object(lc, "disable_and_delete_resource", AsyncMock()))

    def own(self):
        self.service.path, self.service.identifier = PATH, SERVICE

    async def test_accepted_resource_is_owned_before_client_exit_cancellation(self):
        self.client.__aexit__.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.service.create()
        self.assertEqual((self.service.path, self.service.identifier), (PATH, SERVICE))
        self.evidence.assert_called_once()
        self.client.__aexit__.side_effect = None
        self.client.get.return_value = response(code=404)
        with patch.object(self.service, "wait_terminal", AsyncMock(return_value=(resource(), []))):
            self.assertEqual(await self.service.close(), [])
        self.remove.assert_awaited_once()
        self.before.assert_awaited_once_with(SERVICE)
        self.after.assert_awaited_once_with(SERVICE)

    async def test_evidence_failure_cannot_lose_accepted_identity(self):
        self.evidence.side_effect = OSError("evidence disk full")
        with self.assertRaises(OSError):
            await self.service.create()
        self.assertEqual(self.service.path, PATH)

    async def test_invalid_accepted_identity_is_not_owned(self):
        for changes in ({"resourcePath": "/other"}, {"resourceId": "not-uuid"}):
            self.client.post.return_value = accepted(**changes)
            with self.assertRaises(ValueError):
                await self.service.create()
            self.assertIsNone(self.service.path)
        self.evidence.assert_not_called()

    async def test_failed_firewall_pipeline_remains_owned(self):
        with patch.object(
            self.service, "wait_terminal", AsyncMock(return_value=(resource(), [{"status": "pipeline_failed"}]))
        ):
            with self.assertRaisesRegex(RuntimeError, "pipeline"):
                await self.service.create()
        self.assertEqual(self.service.path, PATH)

    async def test_terminal_wait_requires_current_operation_and_pipeline_completion(self):
        self.own()
        self.client.get.side_effect = [
            response({"sharedService": resource()}),
            operations(identifier=OLD_OPERATION),
            response({"sharedService": resource()}),
            operations("updating"),
            response({"sharedService": resource("updated")}),
            operations("pipeline_succeeded"),
        ]
        with patch.object(lc.asyncio, "sleep", AsyncMock()) as sleep:
            result, _ = await self.service.wait_terminal(operation_id=OPERATION)
        self.assertEqual(result["deploymentStatus"], "updated")
        self.assertEqual(sleep.await_count, 2)

    async def test_wait_rejects_changed_ownership(self):
        self.own()
        self.client.get.return_value = response({"sharedService": resource(display_name="another test")})
        with self.assertRaisesRegex(ValueError, "ownership"):
            await self.service.wait_terminal()
        self.remove.assert_not_awaited()

    async def test_action_uses_etag_and_waits_for_returned_operation(self):
        self.own()
        with patch.object(
            self.service,
            "wait_terminal",
            AsyncMock(
                side_effect=[
                    (resource(), []),
                    (resource("action_succeeded"), [{"id": OPERATION, "status": "action_succeeded"}]),
                ]
            ),
        ) as wait:
            await self.service.change(action="stop")
        self.client.post.assert_awaited_once_with(
            "https://tre/api" + PATH + "/invoke-action",
            headers={"Authorization": "Bearer token", "etag": "etag"},
            params={"action": "stop"},
        )
        self.assertEqual(wait.await_args.kwargs, {"operation_id": OPERATION})

    async def test_metadata_update_must_be_preserved(self):
        self.own()
        self.client.patch.return_value = accepted()
        with patch.object(
            self.service,
            "wait_terminal",
            AsyncMock(side_effect=[(resource(), []), (resource("updated"), [{"id": OPERATION, "status": "updated"}])]),
        ):
            with self.assertRaisesRegex(AssertionError, "not preserved"):
                await self.service.change(overview="new text")
        self.assertEqual(self.client.patch.await_args.kwargs["json"], {"properties": {"overview": "new text"}})

    async def test_cleanup_waits_then_guards_then_deletes_and_verifies(self):
        self.own()
        order = []

        async def wait(**kwargs):
            order.append("wait")
            self.assertTrue(kwargs["allow_absent"])
            return resource("deployment_failed"), []

        async def before(identifier):
            order.append("guard")

        async def remove(*args, **kwargs):
            order.append("delete")

        async def after(identifier):
            order.append("verify")

        self.before.side_effect, self.remove.side_effect, self.after.side_effect = before, remove, after
        self.client.get.return_value = response(code=404)
        with patch.object(self.service, "wait_terminal", AsyncMock(side_effect=wait)):
            self.assertEqual(await self.service.close(), [])
        self.assertEqual(order, ["wait", "guard", "delete", "verify"])
        self.assertTrue(self.remove.await_args.kwargs["allow_failed_disable"])

    async def test_cleanup_guard_failure_prevents_delete(self):
        self.own()
        self.before.side_effect = ValueError("foreign tag")
        with patch.object(self.service, "wait_terminal", AsyncMock(return_value=(resource(), []))):
            failures = await self.service.close()
        self.assertIsInstance(failures[0], ValueError)
        self.remove.assert_not_awaited()
        self.after.assert_not_awaited()

    async def test_cleanup_after_api_absence_still_checks_azure(self):
        self.own()
        with patch.object(self.service, "wait_terminal", AsyncMock(return_value=None)):
            self.assertEqual(await self.service.close(), [])
        self.remove.assert_not_awaited()
        self.after.assert_awaited_once_with(SERVICE)

    async def test_cleanup_deadline_bounds_stalled_pipeline_without_delete(self):
        self.own()
        self.service.finish = asyncio.get_running_loop().time() + 0.02

        async def wait(**kwargs):
            await asyncio.sleep(10)

        with patch.object(self.service, "wait_terminal", side_effect=wait):
            failures = await self.service.close()
        self.assertIsInstance(failures[0], TimeoutError)
        self.remove.assert_not_awaited()


class DeadlineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, CYCLECLOUD_VALIDATION_DEADLINE=""))

    async def test_absolute_deadline_counts_container_setup_and_caps_extension(self):
        for deadline, seconds in (("10000", 9000), ("1000000", lc.LIFECYCLE_SECONDS)):
            with (
                patch.dict(os.environ, CYCLECLOUD_VALIDATION_DEADLINE=deadline),
                patch.object(lc.time, "time", return_value=1000),
            ):
                work, finish = lc.lifecycle_deadlines()
            self.assertAlmostEqual(finish - asyncio.get_running_loop().time(), seconds, delta=1)
            self.assertEqual(finish - work, lc.CLEANUP_RESERVE_SECONDS)

    async def test_invalid_or_exhausted_deadline_prevents_provisioning(self):
        for value in ("nan", "inf", "-inf", "invalid", "0"):
            with self.subTest(value=value), patch.dict(os.environ, CYCLECLOUD_VALIDATION_DEADLINE=value):
                with self.assertRaises((ValueError, TimeoutError)):
                    async with lc.cyclecloud_lifecycle(True, PAYLOAD, AsyncMock(), AsyncMock()):
                        self.fail("Invalid deadline reached provisioning")

    async def test_work_timeout_still_runs_cleanup(self):
        now = asyncio.get_running_loop().time()
        with (
            patch.object(lc, "lifecycle_deadlines", return_value=(now + 0.02, now + 1)),
            patch.object(lc.CycleCloudService, "close", AsyncMock(return_value=[])) as close,
        ):
            with self.assertRaises(TimeoutError):
                async with lc.cyclecloud_lifecycle(True, PAYLOAD, AsyncMock(), AsyncMock()):
                    await asyncio.sleep(10)
        close.assert_awaited_once()

    async def test_cleanup_failure_preserves_original_or_fails_successful_case(self):
        cleanup_error = RuntimeError("cleanup failed")
        cleanup_error.add_note(PATH)
        original = ValueError("validation failed")
        with patch.object(lc.CycleCloudService, "close", AsyncMock(return_value=[cleanup_error])):
            with self.assertRaises(ValueError) as raised:
                async with lc.cyclecloud_lifecycle(True, PAYLOAD, AsyncMock(), AsyncMock()):
                    raise original
            self.assertIs(raised.exception, original)
            self.assertIn(PATH, str(original.__notes__))
            with self.assertRaises(ExceptionGroup):
                async with lc.cyclecloud_lifecycle(True, PAYLOAD, AsyncMock(), AsyncMock()):
                    pass

    async def test_repeated_cancellation_waits_for_cleanup(self):
        entered, cleaning, release = (asyncio.Event() for _ in range(3))

        async def close():
            cleaning.set()
            await release.wait()
            return []

        async def run():
            async with lc.cyclecloud_lifecycle(True, PAYLOAD, AsyncMock(), AsyncMock()):
                entered.set()
                await asyncio.sleep(10)

        with patch.object(lc.CycleCloudService, "close", side_effect=close):
            task = asyncio.create_task(run())
            await entered.wait()
            task.cancel()
            await cleaning.wait()
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task


class PrerequisiteTests(unittest.IsolatedAsyncioTestCase):
    async def test_wrong_version_missing_actions_existing_service_or_disabled_firewall_prevents_creation(self):
        catalog = case.load_catalog()
        template = {
            "name": lc.TEMPLATE,
            "version": catalog[lc.TEMPLATE]["source_version"],
            "customActions": [{"name": "start"}, {"name": "stop"}],
        }
        firewall_template = {"name": case.FIREWALL, "version": catalog[case.FIREWALL]["source_version"]}
        firewall = {
            "id": SERVICE,
            "templateName": case.FIREWALL,
            "templateVersion": firewall_template["version"],
            "isEnabled": True,
            "deploymentStatus": "deployed",
        }
        for defect in ("none", "version", "actions", "existing", "disabled"):
            with self.subTest(defect=defect):
                first, deployed = deepcopy(template), deepcopy(firewall)
                services = [deployed]
                if defect == "version":
                    first["version"] = "0.0.0"
                if defect == "actions":
                    first["customActions"] = []
                if defect == "existing":
                    services.append({"templateName": lc.TEMPLATE})
                if defect == "disabled":
                    deployed["isEnabled"] = False
                with (
                    patch.object(case, "get_admin_token", AsyncMock()),
                    patch.object(case, "record_reused_resource"),
                    patch.object(
                        case,
                        "get_resource",
                        AsyncMock(side_effect=[first, firewall_template, {"sharedServices": services}]),
                    ),
                ):
                    if defect == "none":
                        self.assertEqual(await case.prerequisites(True), deployed)
                    else:
                        with self.assertRaises(ValueError):
                            await case.prerequisites(True)
