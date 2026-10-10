import random
import time
import pytest
import asyncio
from typing import Tuple
import config
import logging
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager

from resources.resource import post_resource, disable_and_delete_resource
from resources.workspace import get_workspace_auth_details
from resources import strings as resource_strings
from helpers import get_admin_token, get_template
from e2e_tests.resources.nexus import nexus_prerequisites
from e2e_tests.timeouts import async_test_timeout, cleanup_deadline


LOGGER = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio(loop_scope="session")
CLEANUP_TIMEOUT_SECONDS = 60 * 60
_TEARDOWN_ITEM = pytest.StashKey[pytest.Item]()
_ACTIVE_TIMEOUT = pytest.StashKey[tuple]()
_MANAGED_CLEANUP_USED = pytest.StashKey[bool]()


@pytest.hookimpl(hookwrapper=True, optionalhook=True)
def pytest_timeout_set_timer(item, settings):
    outcome = yield
    if outcome.excinfo is None and outcome.get_result():
        item.stash[_ACTIVE_TIMEOUT] = (settings, time.monotonic())


@pytest.hookimpl(hookwrapper=True, optionalhook=True)
def pytest_timeout_cancel_timer(item):
    yield
    if _ACTIVE_TIMEOUT in item.stash:
        del item.stash[_ACTIVE_TIMEOUT]


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_teardown(item):
    item.session.stash[_TEARDOWN_ITEM] = item


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    if call.when == "teardown" and item.stash.get(_MANAGED_CLEANUP_USED, False):
        # All finalizers have finished. A restored timer must not interrupt
        # traceback formatting and turn an ordinary failure into INTERNALERROR.
        item.config.hook.pytest_timeout_cancel_timer(item=item)


@contextmanager
def pause_test_timeout_for_cleanup(request):
    item = request.session.stash.get(_TEARDOWN_ITEM, None) if request is not None else None
    active = item.stash.get(_ACTIVE_TIMEOUT, None) if item is not None else None
    if active is None or active[0].func_only:
        yield
        return
    settings, started = active
    item.stash[_MANAGED_CLEANUP_USED] = True
    remaining = settings.timeout - (time.monotonic() - started)
    # A timer that already failed the body/setup needs a fresh finite budget for
    # other finalizers. Otherwise preserve the unused budget, excluding cleanup.
    if remaining <= 0:
        remaining = settings.timeout
    item.config.hook.pytest_timeout_cancel_timer(item=item)
    try:
        yield
    finally:
        item.config.hook.pytest_timeout_set_timer(item=item, settings=settings._replace(timeout=remaining))


@asynccontextmanager
async def resource_cleanup_timeout(resource_path, request=None):
    with pause_test_timeout_for_cleanup(request):
        timeout = None
        try:
            async with cleanup_deadline(CLEANUP_TIMEOUT_SECONDS) as timeout:
                yield
        except TimeoutError as error:
            if timeout is None or not timeout.expired():
                raise
            message = f"Cleanup of {resource_path} exceeded {CLEANUP_TIMEOUT_SECONDS} seconds"
            LOGGER.error("%s. Check the operation polling logs for its last observed state.", message)
            raise TimeoutError(message) from error


def pytest_addoption(parser):
    parser.addoption("--verify", action="store", default="true")


@pytest.fixture(scope="session")
def verify(pytestconfig):
    if pytestconfig.getoption("verify").lower() == "true":
        return True
    elif pytestconfig.getoption("verify").lower() == "false":
        return False


@async_test_timeout(60 * 60)
async def create_or_get_test_workspace(
    auth_type: str,
    verify: bool,
    template_name: str = resource_strings.BASE_WORKSPACE,
    pre_created_workspace_id: str = "",
    client_id: str = "",
    client_secret: str = "",
) -> Tuple[str, str]:
    if pre_created_workspace_id != "":
        return f"/workspaces/{pre_created_workspace_id}", pre_created_workspace_id

    LOGGER.info(f"Creating workspace {template_name}")

    description = " ".join([x.capitalize() for x in template_name.split("-")[2:]])
    payload = {
        "templateName": template_name,
        "properties": {
            "display_name": f"E2E {description} workspace ({auth_type} AAD)",
            "description": f"{template_name} test workspace for E2E tests",
            "auth_type": auth_type,
            "address_space_size": "small",
        },
    }

    admin_token = await get_admin_token(verify=verify)
    async with get_template(template_name, resource_strings.API_WORKSPACE_TEMPLATES, admin_token, verify) as response:
        assert response.status_code == 200, (
            f"Failed to GET workspace template '{template_name}': {response.status_code}. Response text: {response.text}"
        )
        template_properties = response.json().get("properties", {})
        if "enable_backup" in template_properties:
            payload["properties"]["enable_backup"] = False

    if config.TEST_WORKSPACE_APP_PLAN != "":
        payload["properties"]["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN

    if auth_type == "Manual":
        payload["properties"]["client_id"] = client_id
        payload["properties"]["client_secret"] = client_secret

    # TODO: Temp fix to solve creation of workspaces - https://github.com/microsoft/AzureTRE/issues/2986
    await asyncio.sleep(random.uniform(1, 9))
    workspace_path, workspace_id = await post_resource(
        payload,
        resource_strings.API_WORKSPACES,
        access_token=admin_token,
        verify=verify,
        cleanup_failed_create=True,
    )

    LOGGER.info(f"Workspace {workspace_id} {template_name} created")
    return workspace_path, workspace_id


@async_test_timeout(60 * 60)
async def create_or_get_test_workpace_service(
    workspace_path, workspace_owner_token, pre_created_workspace_service_id, verify
):
    if pre_created_workspace_service_id != "":
        workspace_service_id = pre_created_workspace_service_id
        workspace_service_path = f"{workspace_path}/{resource_strings.API_WORKSPACE_SERVICES}/{workspace_service_id}"
        return workspace_service_path, workspace_service_id

    # create a guac service
    service_payload = {
        "templateName": resource_strings.GUACAMOLE_SERVICE,
        "properties": {"display_name": "Workspace service test", "description": ""},
    }

    workspace_service_path, workspace_service_id = await post_resource(
        payload=service_payload,
        endpoint=f"/api{workspace_path}/{resource_strings.API_WORKSPACE_SERVICES}",
        access_token=workspace_owner_token,
        verify=verify,
        cleanup_failed_create=True,
    )

    return workspace_service_path, workspace_service_id


async def clean_up_test_workspace(pre_created_workspace_id: str, workspace_path: str, verify: bool, *, request=None):
    # Only delete the workspace if it wasn't pre-created
    if pre_created_workspace_id == "":
        LOGGER.info(f"Deleting workspace {workspace_path}")
        async with resource_cleanup_timeout(workspace_path, request):
            await disable_and_delete_tre_resource(workspace_path, verify)


async def clean_up_test_workspace_service(
    pre_created_workspace_service_id: str, workspace_service_path: str, workspace_id: str, verify: bool, *, request=None
):
    if pre_created_workspace_service_id == "":
        LOGGER.info(f"Deleting workspace service {workspace_service_path}")
        async with resource_cleanup_timeout(workspace_service_path, request):
            await disable_and_delete_ws_resource(workspace_service_path, workspace_id, verify)


# Session scope isn't in effect with python-xdist: https://github.com/microsoft/AzureTRE/issues/2868
@pytest.fixture(scope="session")
async def setup_test_workspace(verify, request) -> Tuple[str, str]:
    pre_created_workspace_id = config.TEST_WORKSPACE_ID
    auth_type = "Manual" if config.TEST_WORKSPACE_APP_ID else "Automatic"
    workspace_path, workspace_id = await create_or_get_test_workspace(
        auth_type=auth_type,
        verify=verify,
        pre_created_workspace_id=pre_created_workspace_id,
        client_id=config.TEST_WORKSPACE_APP_ID,
        client_secret=config.TEST_WORKSPACE_APP_SECRET,
    )

    yield workspace_path, workspace_id

    # Tear-down
    await clean_up_test_workspace(
        pre_created_workspace_id=pre_created_workspace_id, workspace_path=workspace_path, verify=verify, request=request
    )


# Session scope isn't in effect with python-xdist: https://github.com/microsoft/AzureTRE/issues/2868
@pytest.fixture(scope="session")
async def setup_test_workspace_and_guacamole_service(setup_test_workspace, verify, request):
    # Set up
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    pre_created_workspace_service_id = config.TEST_WORKSPACE_SERVICE_ID
    workspace_service_path, workspace_service_id = await create_or_get_test_workpace_service(
        workspace_path,
        workspace_owner_token=workspace_owner_token,
        pre_created_workspace_service_id=pre_created_workspace_service_id,
        verify=verify,
    )

    yield workspace_path, workspace_id, workspace_service_path, workspace_service_id

    await clean_up_test_workspace_service(
        pre_created_workspace_service_id, workspace_service_path, workspace_id, verify, request=request
    )


# Session scope isn't in effect with python-xdist: https://github.com/microsoft/AzureTRE/issues/2868
@pytest.fixture(scope="session")
async def setup_test_aad_workspace(verify, request) -> Tuple[str, str, str]:
    pre_created_workspace_id = config.TEST_AAD_WORKSPACE_ID
    # Set up
    workspace_path, workspace_id = await create_or_get_test_workspace(
        auth_type="Automatic", verify=verify, pre_created_workspace_id=pre_created_workspace_id
    )

    yield workspace_path, workspace_id

    # Tear-down
    await clean_up_test_workspace(
        pre_created_workspace_id=pre_created_workspace_id, workspace_path=workspace_path, verify=verify, request=request
    )


async def get_workspace_owner_token(workspace_id, verify):
    admin_token = await get_admin_token(verify=verify)
    workspace_owner_token, _ = await get_workspace_auth_details(
        admin_token=admin_token, workspace_id=workspace_id, verify=verify
    )
    return workspace_owner_token


async def disable_and_delete_ws_resource(resource_path, workspace_id, verify):
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)
    await disable_and_delete_resource(f"/api{resource_path}", workspace_owner_token, verify, allow_failed_disable=True)


async def disable_and_delete_tre_resource(resource_path, verify):
    admin_token = await get_admin_token(verify)
    await disable_and_delete_resource(f"/api{resource_path}", admin_token, verify, allow_failed_disable=True)


@pytest.fixture(scope="session")
async def setup_nexus_prerequisites(verify, request):
    # Dependencies must outlive review VMs and their workspace finaliser.
    resources = AsyncExitStack()
    try:
        async with asyncio.timeout(60 * 60):
            await resources.enter_async_context(nexus_prerequisites(verify))
        yield
    finally:
        async with resource_cleanup_timeout("Nexus prerequisites", request):
            await resources.aclose()


# Session scope isn't in effect with python-xdist: https://github.com/microsoft/AzureTRE/issues/2868
@pytest.fixture(scope="session")
async def setup_test_airlock_import_review_workspace_and_guacamole_service(
    setup_nexus_prerequisites, verify, request
) -> Tuple[str, str, str, str]:
    pre_created_workspace_id = config.TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_ID
    # Set up
    workspace_path, workspace_id = await create_or_get_test_workspace(
        auth_type="Automatic",
        verify=verify,
        template_name=resource_strings.AIRLOCK_IMPORT_REVIEW_WORKSPACE,
        pre_created_workspace_id=pre_created_workspace_id,
    )

    workspace_service_path = None
    pre_created_workspace_service_id = config.TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_SERVICE_ID
    try:
        admin_token = await get_admin_token(verify=verify)
        workspace_owner_token, _ = await get_workspace_auth_details(
            admin_token=admin_token, workspace_id=workspace_id, verify=verify
        )

        workspace_service_path, workspace_service_id = await create_or_get_test_workpace_service(
            workspace_path,
            workspace_owner_token=workspace_owner_token,
            pre_created_workspace_service_id=pre_created_workspace_service_id,
            verify=verify,
        )

        yield workspace_path, workspace_id, workspace_service_path, workspace_service_id

    finally:
        try:
            # A reused parent has no cascading cleanup. Remove only a child
            # created by this fixture. Preserve any pre-existing service.
            if pre_created_workspace_id and workspace_service_path is not None:
                await clean_up_test_workspace_service(
                    pre_created_workspace_service_id,
                    workspace_service_path,
                    workspace_id,
                    verify,
                    request=request,
                )
        finally:
            await clean_up_test_workspace(
                pre_created_workspace_id=pre_created_workspace_id,
                workspace_path=workspace_path,
                verify=verify,
                request=request,
            )
