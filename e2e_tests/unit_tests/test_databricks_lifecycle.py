"""Check Databricks ownership, pipeline waits and protected prerequisite cleanup."""

import asyncio
from builtins import ExceptionGroup
from functools import partial
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from e2e_tests.resources import databricks_lifecycle as lifecycle

AUTH = "11111111-1111-4111-8111-111111111111"
WORKSPACE = "22222222-2222-4222-8222-222222222222"
SERVICE = "33333333-3333-4333-8333-333333333333"
OPERATION = "44444444-4444-4444-8444-444444444444"
AUTH_PATH = f"/shared-services/{AUTH}"
WORKSPACE_PATH = f"/workspaces/{WORKSPACE}"
SERVICE_PATH = f"{WORKSPACE_PATH}/workspace-services/{SERVICE}"


def owner(kind="service", **changes):
    path, identifier, wrapper, template, workspace_id = {
        "auth": (AUTH_PATH, AUTH, "sharedService", "tre-shared-service-databricks-private-auth", None),
        "workspace": (WORKSPACE_PATH, WORKSPACE, "workspace", "tre-workspace-base", None),
        "service": (SERVICE_PATH, SERVICE, "workspaceService", "tre-service-databricks", WORKSPACE),
    }[kind]
    return lifecycle.OwnedResource(
        path, identifier, wrapper, template, "Databricks validation", "Owned test resource", workspace_id, **changes
    )


def payload(resource, **properties):
    return {
        "templateName": resource.template,
        "properties": {
            "display_name": resource.display_name,
            "description": resource.description,
            **properties,
        },
    }


def response(resource, state="deployed", **changes):
    body = {
        resource.wrapper: {
            "id": resource.identifier,
            "templateName": resource.template,
            "properties": {"display_name": resource.display_name, "description": resource.description},
            "deploymentStatus": state,
            **changes,
        }
    }
    return SimpleNamespace(status_code=200, json=lambda: body)


def operations(*states):
    return SimpleNamespace(
        status_code=200,
        json=lambda: {"operations": [{"id": OPERATION, "status": state} for state in states]},
    )


class DatabricksCreationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        now = asyncio.get_running_loop().time()
        self.resources = lifecycle.DatabricksResources(True, now + 10, now + 20)
        self.admin = self.enterContext(patch.object(lifecycle, "get_admin_token", AsyncMock(return_value="admin")))
        self.owner_token = self.enterContext(
            patch.object(lifecycle, "get_workspace_owner_token", AsyncMock(return_value="owner"))
        )
        self.service = owner()
        self.post = self.enterContext(
            patch.object(lifecycle, "post_resource", AsyncMock(return_value=(SERVICE_PATH, SERVICE)))
        )
        self.wait = self.enterContext(
            patch.object(
                self.resources, "wait_terminal", AsyncMock(return_value=({"deploymentStatus": "deployed"}, []))
            )
        )

    async def test_registers_accepted_service_before_wait_with_owner_token(self):
        before, after = AsyncMock(), AsyncMock()

        async def wait(resource, *, allow_absent):
            self.assertEqual(self.resources.owned, [resource])
            self.assertFalse(allow_absent)
            self.assertEqual((resource.path, resource.identifier), (SERVICE_PATH, SERVICE))
            self.assertIs(resource.before_remove, before)
            self.assertIs(resource.after_remove, after)
            return {"deploymentStatus": "deployed"}, [{"status": "deployed"}]

        self.wait.side_effect = wait
        result = await self.resources.create(
            payload(self.service),
            f"/api{WORKSPACE_PATH}/workspace-services",
            WORKSPACE,
            before_remove=before,
            after_remove=after,
        )
        self.assertEqual(result, (SERVICE_PATH, SERVICE))
        self.post.assert_awaited_once_with(
            payload(self.service), f"/api{WORKSPACE_PATH}/workspace-services", "owner", True, wait=False
        )
        self.owner_token.assert_awaited_once_with(WORKSPACE, True)
        self.admin.assert_not_awaited()

    async def test_fresh_automatic_workspace_uses_admin_token(self):
        workspace = owner("workspace")
        self.post.return_value = WORKSPACE_PATH, WORKSPACE
        await self.resources.create(payload(workspace, auth_type="Automatic"), "/api/workspaces")
        self.admin.assert_awaited_once_with(True)
        self.owner_token.assert_not_awaited()
        self.assertEqual(self.resources.owned[0].wrapper, "workspace")

    async def test_auth_requires_guard_and_protection_before_posting(self):
        auth = owner("auth")
        for options in ({}, {"protected": True}, {"before_remove": AsyncMock()}):
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, "dependency guard"):
                await self.resources.create(payload(auth), "/api/shared-services", **options)
        self.post.assert_not_awaited()

    async def test_auth_ownership_keeps_cleanup_guard(self):
        auth = owner("auth")
        guard = AsyncMock()
        self.post.return_value = AUTH_PATH, AUTH
        await self.resources.create(payload(auth), "/api/shared-services", protected=True, before_remove=guard)
        self.assertTrue(self.resources.owned[0].protected)
        self.assertIs(self.resources.owned[0].before_remove, guard)
        self.admin.assert_awaited_once()

    async def test_invalid_template_parent_or_ownership_metadata_prevents_post(self):
        cases = [
            (payload(self.service), f"/api/workspaces/{AUTH}/workspace-services", WORKSPACE),
            (payload(self.service), f"/api{WORKSPACE_PATH}/workspace-services", None),
            (payload(self.service), "https://other.example/api/shared-services", None),
            (payload(owner("workspace"), auth_type="Manual"), "/api/workspaces", None),
            (payload(self.service, display_name=""), f"/api{WORKSPACE_PATH}/workspace-services", WORKSPACE),
            (payload(self.service, description=""), f"/api{WORKSPACE_PATH}/workspace-services", WORKSPACE),
            ({**payload(self.service), "templateName": "other"}, f"/api{WORKSPACE_PATH}/workspace-services", WORKSPACE),
        ]
        for body, endpoint, workspace_id in cases:
            with self.subTest(body=body, endpoint=endpoint), self.assertRaises(ValueError):
                await self.resources.create(body, endpoint, workspace_id)
        self.post.assert_not_awaited()

    async def test_untrusted_accepted_identity_is_not_owned_or_deleted(self):
        cases = [
            (f"/workspaces/{AUTH}/workspace-services/{SERVICE}", SERVICE),
            (SERVICE_PATH + "/", SERVICE),
            (SERVICE_PATH, "not-a-uuid"),
            (SERVICE_PATH, "00000000-0000-0000-0000-000000000000"),
            (SERVICE_PATH, WORKSPACE),
        ]
        for result in cases:
            with self.subTest(result=result), self.assertRaises(ValueError):
                self.post.return_value = result
                await self.resources.create(
                    payload(self.service), f"/api{WORKSPACE_PATH}/workspace-services", WORKSPACE
                )
        self.assertEqual(self.resources.owned, [])
        self.wait.assert_not_awaited()

    async def test_failed_deployment_and_failed_pipeline_remain_owned(self):
        for state, operation in (("deployment_failed", "deployment_failed"), ("deployed", "pipeline_failed")):
            with self.subTest(state=state, operation=operation):
                self.resources.owned.clear()
                self.wait.return_value = {"deploymentStatus": state}, [{"status": operation}]
                with self.assertRaisesRegex(RuntimeError, "pipeline failed"):
                    await self.resources.create(
                        payload(self.service), f"/api{WORKSPACE_PATH}/workspace-services", WORKSPACE
                    )
                self.assertEqual(self.resources.owned[0].path, SERVICE_PATH)

    async def test_wait_timeout_preserves_accepted_resource(self):
        self.wait.side_effect = TimeoutError("create wait expired")
        with self.assertRaises(TimeoutError):
            await self.resources.create(payload(self.service), f"/api{WORKSPACE_PATH}/workspace-services", WORKSPACE)
        self.assertEqual(self.resources.owned[0].path, SERVICE_PATH)

    async def test_cancelled_deployment_wait_preserves_accepted_resource(self):
        entered = asyncio.Event()

        async def stalled(*args, **kwargs):
            entered.set()
            await asyncio.sleep(10)

        self.wait.side_effect = stalled
        task = asyncio.create_task(
            self.resources.create(payload(self.service), f"/api{WORKSPACE_PATH}/workspace-services", WORKSPACE)
        )
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.resources.owned[0].path, SERVICE_PATH)

    async def test_create_deadline_limits_wait_without_spending_cleanup_reserve(self):
        async def stalled(*args, **kwargs):
            await asyncio.sleep(10)

        self.wait.side_effect = stalled
        with patch.object(lifecycle, "CREATE_SECONDS", 0.02), self.assertRaises(TimeoutError):
            await self.resources.create(payload(self.service), f"/api{WORKSPACE_PATH}/workspace-services", WORKSPACE)
        self.assertEqual(self.resources.owned[0].path, SERVICE_PATH)
        self.assertGreater(self.resources.finish - asyncio.get_running_loop().time(), 10)


class DatabricksPollingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        now = asyncio.get_running_loop().time()
        self.resources = lifecycle.DatabricksResources(True, now + 10, now + 20)
        self.resource = owner()
        self.client = AsyncMock()
        self.client.__aenter__.return_value = self.client
        self.enterContext(patch.object(lifecycle, "AsyncClient", return_value=self.client))
        self.enterContext(patch.object(lifecycle, "get_full_endpoint", side_effect=lambda value: value))
        self.headers = self.enterContext(
            patch.object(lifecycle, "get_auth_header", side_effect=lambda token: {"token": token})
        )
        self.token = self.enterContext(patch.object(self.resources, "token", AsyncMock(side_effect=lambda _: "fresh")))
        self.sleep = self.enterContext(patch.object(lifecycle.asyncio, "sleep", AsyncMock()))
        self.record = self.enterContext(patch.object(lifecycle, "record_operation", Mock()))

    async def test_deployed_resource_waits_for_pending_parent_pipeline(self):
        self.client.get.side_effect = [
            response(self.resource),
            operations("pipeline_running"),
            response(self.resource),
            operations("pipeline_succeeded"),
        ]
        await self.resources.wait_terminal(self.resource, allow_absent=False)
        self.assertEqual(self.client.get.await_count, 4)
        self.assertEqual(self.token.await_count, 4)
        self.sleep.assert_awaited_once_with(30)
        self.record.assert_any_call(f"/api{SERVICE_PATH}/operations/{OPERATION}", "pipeline_running", False)
        self.record.assert_any_call(f"/api{SERVICE_PATH}/operations/{OPERATION}", "pipeline_succeeded", True)

    async def test_failed_deployment_waits_for_all_operations_before_cleanup(self):
        self.client.get.side_effect = [
            response(self.resource, "deployment_failed"),
            operations("deployment_failed", "updating"),
            response(self.resource, "deployment_failed"),
            operations("deployment_failed", "updated"),
        ]
        state, observed = await self.resources.wait_terminal(self.resource, allow_absent=True)
        self.assertEqual(state["deploymentStatus"], "deployment_failed")
        self.assertEqual(len(observed), 2)
        self.sleep.assert_awaited_once_with(30)

    async def test_empty_operation_list_does_not_prove_terminal_creation(self):
        self.client.get.side_effect = [
            response(self.resource),
            operations(),
            response(self.resource),
            operations("deployed"),
        ]
        await self.resources.wait_terminal(self.resource, allow_absent=False)
        self.sleep.assert_awaited_once_with(30)

    async def test_ownership_change_rejects_cleanup_before_operations(self):
        changes = [
            {"id": AUTH},
            {"templateName": "other"},
            {"properties": {"display_name": "other", "description": self.resource.description}},
            {"properties": {"display_name": self.resource.display_name, "description": "other"}},
            {"deploymentStatus": None},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "ownership or deployment status"):
                self.client.get.reset_mock()
                self.client.get.return_value = response(self.resource, **change)
                await self.resources.wait_terminal(self.resource, allow_absent=True)
            self.assertEqual(self.client.get.await_count, 1)

    async def test_missing_resource_is_allowed_only_for_cleanup(self):
        self.client.get.return_value = SimpleNamespace(status_code=404)
        self.assertIsNone(await self.resources.wait_terminal(self.resource, allow_absent=True))
        with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            await self.resources.wait_terminal(self.resource, allow_absent=False)

    async def test_authorisation_failure_is_not_absence(self):
        self.client.get.return_value = SimpleNamespace(status_code=403)
        with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
            await self.resources.wait_terminal(self.resource, allow_absent=True)

    async def test_operations_http_failure_is_not_a_terminal_state(self):
        self.client.get.side_effect = [response(self.resource), SimpleNamespace(status_code=500)]
        with self.assertRaisesRegex(RuntimeError, "HTTP 500"):
            await self.resources.wait_terminal(self.resource, allow_absent=True)

    async def test_removal_requires_404_and_refreshes_token(self):
        self.client.get.side_effect = [response(self.resource, "deleted"), SimpleNamespace(status_code=404)]
        await self.resources.assert_api_removed(self.resource)
        self.assertEqual(self.token.await_count, 2)
        self.sleep.assert_awaited_once_with(10)

    async def test_removal_authorisation_failure_is_not_removal_evidence(self):
        self.client.get.return_value = SimpleNamespace(status_code=403)
        with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
            await self.resources.assert_api_removed(self.resource)


class DatabricksRemovalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        now = asyncio.get_running_loop().time()
        self.resources = lifecycle.DatabricksResources(True, now + 10, now + 20)
        self.events = []

        async def event(name, *args, **kwargs):
            self.events.append(name)
            return "token"

        self.wait = self.enterContext(
            patch.object(self.resources, "wait_terminal", AsyncMock(side_effect=partial(event, "terminal")))
        )
        self.token = self.enterContext(
            patch.object(self.resources, "token", AsyncMock(side_effect=partial(event, "token")))
        )
        self.delete = self.enterContext(
            patch.object(lifecycle, "disable_and_delete_resource", AsyncMock(side_effect=partial(event, "delete")))
        )
        self.absent = self.enterContext(
            patch.object(self.resources, "assert_api_removed", AsyncMock(side_effect=partial(event, "404")))
        )

        async def guard(*args):
            self.events.append("guard")

        async def arm(*args):
            self.events.append("arm")

        self.guard = AsyncMock(side_effect=guard)
        self.arm = AsyncMock(side_effect=arm)
        self.resource = owner("auth", protected=True, before_remove=self.guard, after_remove=self.arm)

    async def test_cleanup_waits_then_guards_deletes_and_verifies_tre_and_arm(self):
        await self.resources.remove(self.resource)
        self.assertEqual(self.events, ["terminal", "guard", "token", "delete", "404", "arm"])
        self.wait.assert_awaited_once_with(self.resource, allow_absent=True)
        self.guard.assert_awaited_once_with(AUTH_PATH, AUTH)
        self.arm.assert_awaited_once_with(AUTH_PATH, AUTH)
        self.delete.assert_awaited_once_with(f"/api{AUTH_PATH}", "token", True, allow_failed_disable=True)

    async def test_guard_failure_prevents_auth_deletion(self):
        self.guard.side_effect = RuntimeError("active TRE workspace remains")
        with self.assertRaisesRegex(RuntimeError, "active TRE workspace"):
            await self.resources.remove(self.resource)
        self.delete.assert_not_awaited()
        self.arm.assert_not_awaited()

    async def test_absent_tre_resource_still_needs_arm_removal_evidence(self):
        self.wait.side_effect = None
        self.wait.return_value = None
        await self.resources.remove(self.resource)
        self.delete.assert_not_awaited()
        self.arm.assert_awaited_once_with(AUTH_PATH, AUTH)

    async def test_dependencies_are_removed_in_reverse_order(self):
        auth = self.resource
        workspace, service = owner("workspace"), owner()
        self.resources.owned.extend((auth, workspace, service))
        removed = []

        async def remove(resource):
            removed.append(resource.path)

        with patch.object(self.resources, "remove", side_effect=remove):
            self.assertEqual(await self.resources.close(), [])
        self.assertEqual(removed, [SERVICE_PATH, WORKSPACE_PATH, AUTH_PATH])

    async def test_dependent_failure_attempts_workspace_cleanup_and_preserves_auth(self):
        self.resources.owned.extend((self.resource, owner("workspace"), owner()))
        removed = []

        async def remove(resource):
            removed.append(resource.path)
            if resource.path == SERVICE_PATH:
                raise TimeoutError("Databricks managed resource group remains")

        with patch.object(self.resources, "remove", side_effect=remove):
            failures = await self.resources.close()
        self.assertEqual(removed, [SERVICE_PATH, WORKSPACE_PATH])
        self.assertEqual(len(failures), 2)
        self.assertIn("retained", str(failures[1]))
        self.assertIn(SERVICE_PATH, " ".join(failures[0].__notes__))

    async def test_failed_workspace_cleanup_preserves_auth(self):
        self.resources.owned.extend((self.resource, owner("workspace")))
        with patch.object(self.resources, "remove", AsyncMock(side_effect=RuntimeError("workspace remains"))) as remove:
            failures = await self.resources.close()
        self.assertEqual(remove.await_count, 1)
        self.assertEqual(len(failures), 2)
        self.assertIn("retained", str(failures[-1]))


class DatabricksDeadlineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, DATABRICKS_VALIDATION_DEADLINE=""))

    async def test_absolute_deadline_counts_time_before_start(self):
        with (
            patch.dict(os.environ, DATABRICKS_VALIDATION_DEADLINE="10000"),
            patch.object(lifecycle.time, "time", return_value=1000),
        ):
            work, finish = lifecycle.lifecycle_deadlines()
        self.assertAlmostEqual(finish - asyncio.get_running_loop().time(), 9000, delta=1)
        self.assertEqual(finish - work, 7200)

    async def test_late_configured_deadline_cannot_extend_maximum_lifetime(self):
        with (
            patch.dict(os.environ, DATABRICKS_VALIDATION_DEADLINE="1000000"),
            patch.object(lifecycle.time, "time", return_value=1000),
        ):
            _, finish = lifecycle.lifecycle_deadlines()
        self.assertAlmostEqual(finish - asyncio.get_running_loop().time(), 270 * 60, delta=1)

    async def test_invalid_or_exhausted_deadline_prevents_provisioning(self):
        for value in ("nan", "inf", "-inf", "invalid", "0"):
            with self.subTest(value=value), patch.dict(os.environ, DATABRICKS_VALIDATION_DEADLINE=value):
                with self.assertRaises((ValueError, TimeoutError)):
                    async with lifecycle.databricks_lifecycle(True):
                        self.fail("Invalid deadline reached provisioning")

    async def test_stalled_service_leaves_parent_cleanup_time_and_retains_auth(self):
        now = asyncio.get_running_loop().time()
        resources = lifecycle.DatabricksResources(True, now, now + 0.3)
        resources.owned.extend((owner("auth", protected=True), owner("workspace"), owner()))
        removed = []

        async def remove(resource):
            removed.append(resource.path)
            if resource.path == SERVICE_PATH:
                await asyncio.sleep(10)

        with patch.object(resources, "remove", side_effect=remove):
            failures = await resources.close()
        self.assertEqual(removed, [SERVICE_PATH, WORKSPACE_PATH])
        self.assertIsInstance(failures[0], TimeoutError)
        self.assertIn("retained", str(failures[1]))
        self.assertLess(asyncio.get_running_loop().time(), resources.finish)

    async def test_work_timeout_preserves_cleanup_reserve(self):
        now = asyncio.get_running_loop().time()
        cleanup = AsyncMock(return_value=[])
        with (
            patch.object(lifecycle, "lifecycle_deadlines", return_value=(now + 0.02, now + 1)),
            patch.object(lifecycle.DatabricksResources, "close", cleanup),
        ):
            with self.assertRaises(TimeoutError):
                async with lifecycle.databricks_lifecycle(True):
                    await asyncio.sleep(10)
        cleanup.assert_awaited_once()

    async def test_cleanup_failure_preserves_original_error_with_evidence(self):
        original = ValueError("configuration validation failed")
        with patch.object(
            lifecycle.DatabricksResources, "remove", AsyncMock(side_effect=RuntimeError("cleanup failed"))
        ):
            with self.assertRaises(ValueError) as raised:
                async with lifecycle.databricks_lifecycle(True) as resources:
                    resources.owned.append(owner())
                    raise original
        self.assertIs(raised.exception, original)
        self.assertIn("cleanup failed", " ".join(original.__notes__))
        self.assertIn(SERVICE_PATH, " ".join(original.__notes__))

    async def test_cleanup_failure_without_original_error_fails_case(self):
        with patch.object(
            lifecycle.DatabricksResources, "remove", AsyncMock(side_effect=RuntimeError("cleanup failed"))
        ):
            with self.assertRaises(ExceptionGroup) as raised:
                async with lifecycle.databricks_lifecycle(True) as resources:
                    resources.owned.append(owner())
        self.assertEqual(str(raised.exception.exceptions[0]), "cleanup failed")

    async def test_repeated_cancellation_waits_for_cleanup_and_preserves_cancellation(self):
        entered, cleaning, release, finished = (asyncio.Event() for _ in range(4))

        async def remove(resource):
            cleaning.set()
            await release.wait()
            finished.set()

        async def run():
            async with lifecycle.databricks_lifecycle(True) as resources:
                resources.owned.append(owner())
                entered.set()
                await asyncio.sleep(10)

        with patch.object(lifecycle.DatabricksResources, "remove", side_effect=remove):
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
        self.assertTrue(finished.is_set())

    async def test_cancelled_child_cleanup_does_not_skip_parent_or_remove_auth(self):
        now = asyncio.get_running_loop().time()
        resources = lifecycle.DatabricksResources(True, now, now + 1)
        resources.owned.extend((owner("auth", protected=True), owner("workspace"), owner()))
        with patch.object(resources, "remove", AsyncMock(side_effect=[asyncio.CancelledError(), None])) as remove:
            failures = await resources.close()
        self.assertEqual(remove.await_count, 2)
        self.assertIsInstance(failures[0], asyncio.CancelledError)
        self.assertIn("retained", str(failures[1]))
