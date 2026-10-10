"""Exercise AML ownership, prerequisite ordering and bounded recovery without Azure."""

import asyncio
from builtins import ExceptionGroup
from contextlib import asynccontextmanager
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from e2e_tests import test_aml as aml
from e2e_tests.resources import aml_lifecycle as lifecycle
from e2e_tests.timeouts import cleanup_deadline

SUBSCRIPTION = "00000000-0000-4000-8000-000000000001"
TENANT = "00000000-0000-4000-8000-000000000002"
USER = "00000000-0000-4000-8000-000000000003"
WORKSPACE = "11111111-1111-4111-8111-111111111111"
SERVICE = "22222222-2222-4222-8222-222222222222"
COMPUTE = "33333333-3333-4333-8333-333333333333"
WORKSPACE_PATH = f"/workspaces/{WORKSPACE}"
SERVICE_PATH = f"{WORKSPACE_PATH}/workspace-services/{SERVICE}"
COMPUTE_PATH = f"{SERVICE_PATH}/user-resources/{COMPUTE}"


class AMLOrchestrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.events = []
        self.enterContext(
            patch.dict(
                os.environ,
                ARM_SUBSCRIPTION_ID=SUBSCRIPTION,
                ARM_TENANT_ID=TENANT,
                AZURE_ENVIRONMENT="AzureCloud",
                TEST_AML_USER_OBJECT_ID=USER,
                AML_VALIDATION_DEADLINE="",
            )
        )
        for name, value in (
            ("TRE_ID", "tre-test"),
            ("AAD_TENANT_ID", TENANT),
            ("TEST_WORKSPACE_APP_ID", "manual-app"),
            ("TEST_WORKSPACE_ID", "existing-workspace"),
            ("TEST_WORKSPACE_SERVICE_ID", "existing-service"),
        ):
            self.enterContext(patch.object(aml.config, name, value))
        self.workspace_properties = {
            "auth_type": "Automatic",
            "workspace_owners_group_id": "44444444-4444-4444-8444-444444444444",
            "workspace_researchers_group_id": "55555555-5555-4555-8555-555555555555",
        }
        self.bad_version = None
        self.bad_template = None
        self.missing_template = None
        self.public_service = False
        self.foreign_service = False
        self.fail_compute_create = False
        self.fail_compute_state = False
        self.group, self.aml_id, self.subnet, self.compute_id = aml.resource_ids(
            SUBSCRIPTION, "tre-test", WORKSPACE, SERVICE, COMPUTE
        )
        self.create_workspace = self.enterContext(
            patch.object(lifecycle, "create_or_get_test_workspace", AsyncMock(return_value=(WORKSPACE_PATH, WORKSPACE)))
        )
        self.enterContext(patch.object(lifecycle, "get_workspace_owner_token", AsyncMock(return_value="owner")))
        self.enterContext(patch.object(lifecycle, "get_admin_token", AsyncMock(return_value="admin")))
        self.enterContext(patch.object(aml, "get_workspace_owner_token", AsyncMock(return_value="owner")))
        self.enterContext(patch.object(aml, "get_admin_token", AsyncMock(return_value="admin")))

        async def create(payload, endpoint, token, verify, *, cleanup_failed_create):
            self.assertTrue(cleanup_failed_create)
            if payload["templateName"] == aml.strings.AZUREML_SERVICE:
                self.assertEqual(endpoint, f"/api{WORKSPACE_PATH}/workspace-services")
                self.assertIs(payload["properties"]["is_exposed_externally"], False)
                self.events.append("create-service")
                return SERVICE_PATH, SERVICE
            self.assertEqual(endpoint, f"/api{SERVICE_PATH}/user-resources")
            self.assertEqual(payload["properties"]["vm_size"], "Standard_D2_v3")
            self.assertEqual(payload["properties"]["user_object_id"], USER)
            self.events.append("create-compute")
            if self.fail_compute_create:
                raise RuntimeError("accepted compute create failed")
            return COMPUTE_PATH, COMPUTE

        async def remove(endpoint, token, verify, *, allow_failed_disable):
            self.assertTrue(allow_failed_disable)
            self.events.append("delete:" + endpoint.removeprefix("/api"))

        self.post = self.enterContext(patch.object(lifecycle, "post_resource", AsyncMock(side_effect=create)))
        self.enterContext(patch.object(lifecycle, "disable_and_delete_resource", AsyncMock(side_effect=remove)))
        self.api_removed = self.enterContext(patch.object(lifecycle, "assert_api_removed", AsyncMock()))
        self.arm_removed = self.enterContext(patch.object(lifecycle, "assert_removed", AsyncMock()))

        async def read(endpoint, *_):
            resource_id = endpoint.rsplit("/", 1)[1]
            if "-templates/" in endpoint:
                if resource_id == self.missing_template:
                    raise AssertionError("template returned HTTP 404")
                return {
                    "name": resource_id,
                    "version": "old"
                    if self.bad_template == resource_id
                    else aml.load_catalog()[resource_id]["source_version"],
                }
            resource_key, template, properties = {
                WORKSPACE: ("workspace", aml.strings.BASE_WORKSPACE, self.workspace_properties),
                SERVICE: (
                    "workspaceService",
                    aml.strings.AZUREML_SERVICE,
                    {"is_exposed_externally": False, "azureml_workspace_name": self.aml_id.rsplit("/", 1)[1]},
                ),
                COMPUTE: ("userResource", aml.COMPUTE_TEMPLATE, {"vm_size": aml.VM_SIZE, "user_object_id": USER}),
            }[resource_id]
            return {
                resource_key: {
                    "id": resource_id,
                    "templateName": template,
                    "templateVersion": "old"
                    if self.bad_version == resource_id
                    else aml.load_catalog()[template]["source_version"],
                    "deploymentStatus": "deployed",
                    "properties": properties,
                }
            }

        async def arm_request(method, identifier, api):
            if identifier == self.group:
                return {"id": identifier}
            self.assertEqual(identifier, self.aml_id)
            return {
                "id": identifier,
                "tags": {
                    "tre_id": "tre-test",
                    "tre_workspace_id": "other" if self.foreign_service else WORKSPACE,
                    "tre_workspace_service_id": SERVICE,
                },
                "properties": {
                    "provisioningState": "Succeeded",
                    "publicNetworkAccess": "Enabled" if self.public_service else "Disabled",
                },
            }

        self.arm = SimpleNamespace(request=AsyncMock(side_effect=arm_request))

        @asynccontextmanager
        async def arm_client():
            yield self.arm

        async def compute(*args):
            self.events.append("compute-running")
            self.assertEqual(
                args,
                (
                    self.arm,
                    self.compute_id,
                    self.subnet,
                    {
                        "tre_id": "tre-test",
                        "tre_workspace_id": WORKSPACE,
                        "tre_workspace_service_id": SERVICE,
                        "tre_user_resource_id": COMPUTE,
                    },
                    TENANT,
                    USER,
                ),
            )
            if self.fail_compute_state:
                raise AssertionError("AML compute provisioning failed: Failed")

        self.enterContext(patch.object(aml, "arm_client", arm_client))
        self.enterContext(patch.object(aml, "get_resource", read))
        self.record = self.enterContext(patch.object(aml, "record_deployed_resource", Mock()))
        self.compute = self.enterContext(patch.object(aml, "wait_for_compute", AsyncMock(side_effect=compute)))

    async def test_compute_uses_fresh_automatic_workspace_and_deletes_dependencies_in_order(self):
        await aml.test_private_aml_compute_lifecycle(True)
        self.create_workspace.assert_awaited_once_with(auth_type="Automatic", verify=True, pre_created_workspace_id="")
        self.assertEqual(
            self.events,
            [
                "create-service",
                "create-compute",
                "compute-running",
                "delete:" + COMPUTE_PATH,
                "delete:" + SERVICE_PATH,
                "delete:" + WORKSPACE_PATH,
            ],
        )
        self.assertEqual(
            [call.args[0] for call in self.api_removed.await_args_list], [COMPUTE_PATH, SERVICE_PATH, WORKSPACE_PATH]
        )
        self.assertEqual([call.args[1] for call in self.arm_removed.await_args_list], [self.compute_id, self.aml_id])
        self.assertEqual(
            [call.args[1] for call in self.record.call_args_list], [WORKSPACE_PATH, SERVICE_PATH, COMPUTE_PATH]
        )

    async def test_parent_case_needs_no_assigned_user_and_creates_no_compute(self):
        os.environ["TEST_AML_USER_OBJECT_ID"] = ""
        await aml.test_private_aml_service_lifecycle(True)
        self.assertEqual(self.post.await_count, 1)
        self.compute.assert_not_awaited()
        self.assertEqual(self.events[-2:], ["delete:" + SERVICE_PATH, "delete:" + WORKSPACE_PATH])

    async def test_missing_assigned_user_fails_before_creating_workspace(self):
        os.environ["TEST_AML_USER_OBJECT_ID"] = ""
        with self.assertRaisesRegex(ValueError, "TEST_AML_USER_OBJECT_ID"):
            await aml.test_private_aml_compute_lifecycle(True)
        self.create_workspace.assert_not_awaited()
        self.post.assert_not_awaited()

    async def test_missing_automatic_group_prevents_parent_creation_and_cleans_workspace(self):
        self.workspace_properties.pop("workspace_owners_group_id")
        with self.assertRaisesRegex(ValueError, "workspace_owners_group_id"):
            await aml.test_private_aml_compute_lifecycle(True)
        self.post.assert_not_awaited()
        self.assertEqual(self.events, ["delete:" + WORKSPACE_PATH])

    async def test_nil_workspace_group_prevents_parent_creation(self):
        self.workspace_properties["workspace_researchers_group_id"] = "00000000-0000-0000-0000-000000000000"
        with self.assertRaisesRegex(ValueError, "workspace_researchers_group_id"):
            await aml.test_private_aml_compute_lifecycle(True)
        self.post.assert_not_awaited()

    async def test_unregistered_compute_template_fails_before_workspace_creation(self):
        self.missing_template = aml.COMPUTE_TEMPLATE
        with self.assertRaisesRegex(AssertionError, "HTTP 404"):
            await aml.test_private_aml_compute_lifecycle(True)
        self.create_workspace.assert_not_awaited()

    async def test_old_parent_template_fails_before_workspace_creation(self):
        self.bad_template = aml.strings.AZUREML_SERVICE
        with self.assertRaisesRegex(AssertionError, "Register the checkout version"):
            await aml.test_private_aml_compute_lifecycle(True)
        self.create_workspace.assert_not_awaited()

    async def test_other_subscription_prevents_parent_creation(self):
        self.workspace_properties["workspace_subscription_id"] = USER
        with self.assertRaisesRegex(ValueError, "same subscription"):
            await aml.test_private_aml_compute_lifecycle(True)
        self.post.assert_not_awaited()
        self.assertEqual(self.events, ["delete:" + WORKSPACE_PATH])

    async def test_public_or_unowned_service_prevents_compute_creation(self):
        for setting, message in (("public_service", "public access"), ("foreign_service", "ownership tags")):
            with self.subTest(setting=setting):
                setattr(self, setting, True)
                self.events.clear()
                with self.assertRaisesRegex(AssertionError, message):
                    await aml.test_private_aml_compute_lifecycle(True)
                self.assertNotIn("create-compute", self.events)
                self.assertEqual(self.events[-2:], ["delete:" + SERVICE_PATH, "delete:" + WORKSPACE_PATH])
                setattr(self, setting, False)

    async def test_old_deployed_version_is_recorded_before_failure_and_cleanup(self):
        self.bad_version = COMPUTE
        with self.assertRaisesRegex(AssertionError, "differs from this checkout"):
            await aml.test_private_aml_compute_lifecycle(True)
        self.assertEqual(self.record.call_args.args[0]["templateVersion"], "old")
        self.compute.assert_not_awaited()
        self.assertEqual(
            self.events[-3:], ["delete:" + COMPUTE_PATH, "delete:" + SERVICE_PATH, "delete:" + WORKSPACE_PATH]
        )

    async def test_failed_compute_create_keeps_parent_cleanup(self):
        self.fail_compute_create = True
        with self.assertRaisesRegex(RuntimeError, "accepted compute create failed"):
            await aml.test_private_aml_compute_lifecycle(True)
        self.compute.assert_not_awaited()
        self.assertEqual(self.events[-2:], ["delete:" + SERVICE_PATH, "delete:" + WORKSPACE_PATH])

    async def test_failed_compute_state_still_checks_all_removals(self):
        self.fail_compute_state = True
        with self.assertRaisesRegex(AssertionError, "provisioning failed"):
            await aml.test_private_aml_compute_lifecycle(True)
        self.assertEqual(
            self.events[-3:], ["delete:" + COMPUTE_PATH, "delete:" + SERVICE_PATH, "delete:" + WORKSPACE_PATH]
        )
        self.assertEqual(self.arm_removed.await_count, 2)

    async def test_failed_arm_removal_keeps_parent_cleanup_and_fails_the_case(self):
        self.arm_removed.side_effect = [TimeoutError("compute remains"), None]
        with self.assertRaises(ExceptionGroup) as raised:
            await aml.test_private_aml_compute_lifecycle(True)
        self.assertIn("compute remains", repr(raised.exception.exceptions))
        self.assertEqual(
            self.events[-3:], ["delete:" + COMPUTE_PATH, "delete:" + SERVICE_PATH, "delete:" + WORKSPACE_PATH]
        )


class AMLDeadlineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, AML_VALIDATION_DEADLINE=""))

    async def test_absolute_deadline_counts_time_before_test_start(self):
        with (
            patch.dict(os.environ, AML_VALIDATION_DEADLINE="10000"),
            patch.object(lifecycle.time, "time", return_value=1000),
        ):
            work, finish = lifecycle.lifecycle_deadlines()
        self.assertAlmostEqual(finish - asyncio.get_running_loop().time(), 9000, delta=1)
        self.assertEqual(finish - work, 7200)

    async def test_invalid_or_exhausted_deadlines_fail_before_yield(self):
        for value in ("nan", "inf", "-inf", "invalid", "0"):
            with self.subTest(value=value), patch.dict(os.environ, AML_VALIDATION_DEADLINE=value):
                with self.assertRaises((ValueError, TimeoutError)):
                    async with lifecycle.aml_lifecycle(True):
                        self.fail("An invalid deadline reached provisioning")

    async def test_stalled_child_does_not_prevent_parent_cleanup(self):
        now = asyncio.get_running_loop().time()
        resources = lifecycle.AMLResources(True, now, now + 0.2)
        parent = AsyncMock()
        resources.own("parent", parent)
        resources.own("child", asyncio.sleep, 10)
        failures = await resources.close()
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], TimeoutError)
        parent.assert_awaited_once()

    async def test_failed_create_recovery_leaves_reserve_for_existing_parents(self):
        now = asyncio.get_running_loop().time()
        resources = lifecycle.AMLResources(True, now, now + 0.4)
        parent = AsyncMock()
        resources.own("parent", parent)
        with self.assertRaises(TimeoutError):
            async with resources.creation():
                async with cleanup_deadline(10):
                    await asyncio.sleep(10)
        self.assertLess(asyncio.get_running_loop().time(), resources.finish)
        self.assertEqual(await resources.close(), [])
        parent.assert_awaited_once()

    async def test_work_timeout_keeps_cleanup_reserve(self):
        now = asyncio.get_running_loop().time()
        cleanup = AsyncMock()
        with patch.object(lifecycle, "lifecycle_deadlines", return_value=(now + 0.02, now + 1)):
            with self.assertRaises(TimeoutError):
                async with lifecycle.aml_lifecycle(True) as resources:
                    resources.own("owned", cleanup)
                    await asyncio.sleep(10)
        cleanup.assert_awaited_once()

    async def test_cleanup_failure_preserves_original_error(self):
        error = ValueError("validation failed")
        with self.assertRaises(ValueError) as raised:
            async with lifecycle.aml_lifecycle(True) as resources:
                resources.own("owned", AsyncMock(side_effect=RuntimeError("cleanup failed")))
                raise error
        self.assertIs(raised.exception, error)
        self.assertIn("cleanup failed", " ".join(error.__notes__))

    async def test_repeated_cancellation_waits_for_cleanup(self):
        entered, cleaning, release, finished = (asyncio.Event() for _ in range(4))

        async def remove():
            cleaning.set()
            await release.wait()
            finished.set()

        async def run():
            async with lifecycle.aml_lifecycle(True) as resources:
                resources.own("owned", remove)
                entered.set()
                await asyncio.sleep(10)

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

    async def test_cancelled_child_finaliser_does_not_skip_parent(self):
        now = asyncio.get_running_loop().time()
        resources = lifecycle.AMLResources(True, now, now + 1)
        parent = AsyncMock()
        resources.own("parent", parent)
        resources.own("child", AsyncMock(side_effect=asyncio.CancelledError()))
        failures = await resources.close()
        parent.assert_awaited_once()
        self.assertIsInstance(failures[0], asyncio.CancelledError)


class AMLRemovalTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_removal_waits_for_404(self):
        client = AsyncMock()
        client.get.side_effect = [SimpleNamespace(status_code=200), SimpleNamespace(status_code=404)]
        client.__aenter__.return_value = client
        with (
            patch.object(lifecycle, "AsyncClient", return_value=client),
            patch.object(lifecycle, "get_full_endpoint", side_effect=lambda value: value),
            patch.object(lifecycle, "get_auth_header", return_value={}),
            patch.object(lifecycle.asyncio, "sleep", AsyncMock()),
        ):
            await lifecycle.assert_api_removed(COMPUTE_PATH, "token", True)
        self.assertEqual(client.get.await_count, 2)

    async def test_api_authorisation_failure_is_not_removal_evidence(self):
        client = AsyncMock()
        client.get.return_value = SimpleNamespace(status_code=403)
        client.__aenter__.return_value = client
        with (
            patch.object(lifecycle, "AsyncClient", return_value=client),
            patch.object(lifecycle, "get_full_endpoint", side_effect=lambda value: value),
            patch.object(lifecycle, "get_auth_header", return_value={}),
        ):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
                await lifecycle.assert_api_removed(COMPUTE_PATH, "token", True)
