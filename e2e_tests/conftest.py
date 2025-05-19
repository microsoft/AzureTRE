import json
import os
from pathlib import Path
import random
import uuid
from filelock import FileLock
import pytest
import asyncio
from typing import Tuple, AsyncGenerator
import config
import logging

from resources.resource import post_resource, disable_and_delete_resource
from resources.workspace import get_workspace_auth_details
from resources import strings as resource_strings
from helpers import get_admin_token


LOGGER = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio(loop_scope="session")


def pytest_addoption(parser):
    parser.addoption("--verify", action="store", default="true")


def pytest_configure(config):
    if os.environ.get("PYTEST_RUN_NUMBER") is None:
        pytest_run_number = str(uuid.uuid4())
        os.environ["PYTEST_RUN_NUMBER"] = pytest_run_number
    else:
        pytest_run_number = os.environ.get("PYTEST_RUN_NUMBER")
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id is not None:
        logging.basicConfig(
            format=config.getini("log_file_format"),
            filename=f"pytest_log_{pytest_run_number}_{worker_id}.log",
            level=config.getini("log_file_level"),
        )
    else:
        logging.basicConfig(
            format=config.getini("log_file_format"),
            filename=f"pytest_log_{pytest_run_number}.log",
            level=config.getini("log_file_level"),
        )


@pytest.fixture(scope="session")
def verify(pytestconfig):
    if pytestconfig.getoption("verify").lower() == "true":
        return True
    elif pytestconfig.getoption("verify").lower() == "false":
        return False


async def create_or_get_test_workspace(
        auth_type: str,
        verify: bool,
        template_name: str = resource_strings.BASE_WORKSPACE,
        pre_created_workspace_id: str = "",
        client_id: str = "",
        client_secret: str = "") -> Tuple[str, str]:
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
            "address_space_size": "small"
        }
    }
    if config.TEST_WORKSPACE_APP_PLAN != "":
        payload["properties"]["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN

    if auth_type == "Manual":
        payload["properties"]["client_id"] = client_id
        payload["properties"]["client_secret"] = client_secret
    else:
        payload["properties"]["create_aad_groups"] = True

    admin_token = await get_admin_token(verify=verify)
    # TODO: Temp fix to solve creation of workspaces - https://github.com/microsoft/AzureTRE/issues/2986
    await asyncio.sleep(random.uniform(1, 9))

    workspace_path, workspace_id = await post_resource(payload, resource_strings.API_WORKSPACES, access_token=admin_token, verify=verify)

    LOGGER.info(f"Workspace {workspace_id} {template_name} created")
    return workspace_path, workspace_id


async def create_or_get_test_workpace_service(workspace_path, workspace_owner_token, pre_created_workspace_service_id, verify):
    if pre_created_workspace_service_id != "":
        workspace_service_id = pre_created_workspace_service_id
        workspace_service_path = f"{workspace_path}/{resource_strings.API_WORKSPACE_SERVICES}/{workspace_service_id}"
        return workspace_service_path, workspace_service_id

    # create a guac service
    service_payload = {
        "templateName": resource_strings.GUACAMOLE_SERVICE,
        "properties": {
            "display_name": "Workspace service test",
            "description": ""
        }
    }

    workspace_service_path, workspace_service_id = await post_resource(
        payload=service_payload,
        endpoint=f'/api{workspace_path}/{resource_strings.API_WORKSPACE_SERVICES}',
        access_token=workspace_owner_token,
        verify=verify)

    return workspace_service_path, workspace_service_id


async def clean_up_test_workspace(pre_created_workspace_id: str, workspace_path: str, verify: bool):
    # Only delete the workspace if it wasn't pre-created
    if pre_created_workspace_id == "":
        LOGGER.info(f"Deleting workspace {pre_created_workspace_id}")
        await disable_and_delete_tre_resource(workspace_path, verify)


async def clean_up_test_workspace_service(pre_created_workspace_service_id: str, workspace_service_path: str, workspace_id: str, verify: bool):
    if pre_created_workspace_service_id == "":
        LOGGER.info(f"Deleting workspace service {pre_created_workspace_service_id}")
        await disable_and_delete_ws_resource(workspace_service_path, workspace_id, verify)


def read_json_file(file_path: Path) -> dict:
    return json.loads(file_path.read_text().replace("'", '"'))


def write_json_file(file_path: Path, data: dict):
    file_path.write_text(json.dumps(data))


async def setup_test_base_workspace_with_locks(worker_id: str, tmp_path_factory, verify) -> AsyncGenerator[Tuple[str, str], None]:
    LOCK_SUFFIX = ".lock"
    WORKSPACE_DETAILS_FILE = "setup_test_workspace.json"
    WORKER_LOCKS_DIR = "worker_locks"

    root_tmp_dir = tmp_path_factory.getbasetemp().parent
    fn = root_tmp_dir / WORKSPACE_DETAILS_FILE
    lock_fn = root_tmp_dir / (WORKSPACE_DETAILS_FILE + LOCK_SUFFIX)
    worker_lock_dir = root_tmp_dir / WORKER_LOCKS_DIR
    worker_lock = worker_lock_dir / worker_id

    # Ensure worker lock directory exists
    worker_lock_dir.mkdir(parents=True, exist_ok=True)
    worker_lock.touch()

    try:
        if worker_id == "master":
            workspace_path, workspace_id = await create_or_get_test_workspace(
                auth_type="Automatic",
                pre_created_workspace_id=config.TEST_WORKSPACE_ID,
                client_id=config.TEST_WORKSPACE_APP_ID,
                client_secret=config.TEST_WORKSPACE_APP_SECRET,
                verify=verify
            )
        else:
            with FileLock(lock_fn):
                if fn.is_file():
                    data = read_json_file(fn)
                    workspace_path = data["workspace_path"]
                    workspace_id = data["workspace_id"]
                else:
                    workspace_path, workspace_id = await create_or_get_test_workspace(
                        auth_type="Automatic",
                        pre_created_workspace_id=config.TEST_WORKSPACE_ID,
                        client_id=config.TEST_WORKSPACE_APP_ID,
                        client_secret=config.TEST_WORKSPACE_APP_SECRET,
                        verify=verify
                    )
                    data = {
                        "workspace_path": workspace_path,
                        "workspace_id": workspace_id
                    }
                    write_json_file(fn, data)

        yield workspace_path, workspace_id

    finally:
        # Tear-down logic
        try:
            if len(list(worker_lock_dir.glob("*"))) > 1:
                worker_lock.unlink(missing_ok=True)
                while len(list(worker_lock_dir.glob("*"))) > 0:
                    await asyncio.sleep(10)
            elif len(list(worker_lock_dir.glob("*"))) == 1:
                await clean_up_test_workspace(
                    pre_created_workspace_id=config.TEST_WORKSPACE_ID,
                    workspace_path=workspace_path,
                    verify=verify
                )
                worker_lock.unlink(missing_ok=True)
        except Exception as e:
            LOGGER.error(f"Error during workspace cleanup: {e}")


@pytest.fixture(scope="session")
async def setup_test_base_workspace_and_guacamole_service(setup_test_base_workspace, verify):
    # Set up
    workspace_path, workspace_id = setup_test_base_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    pre_created_workspace_service_id = config.TEST_GUACAMOLE_WORKSPACE_SERVICE_ID
    workspace_service_path, workspace_service_id = await create_or_get_test_workpace_service(
        workspace_path,
        workspace_owner_token=workspace_owner_token,
        pre_created_workspace_service_id=pre_created_workspace_service_id,
        verify=verify)

    yield workspace_path, workspace_id, workspace_service_path, workspace_service_id

    await clean_up_test_workspace_service(pre_created_workspace_service_id, workspace_service_path, workspace_id, verify)


@pytest.fixture(scope="session")
async def setup_airlock_test_workspaces_and_guacamole_service(worker_id, tmp_path_factory, verify):
    # Start both async generators concurrently and get their first yielded values
    base_workspace_function = setup_test_base_workspace_with_locks(worker_id, tmp_path_factory, verify)
    airlock_function = setup_test_airlock_import_review_workspace_and_guacamole_service(verify)
    base_result, airlock_result = await asyncio.gather(base_workspace_function.__anext__(), airlock_function.__anext__())
    try:
        yield (*base_result, *airlock_result)
    finally:
        await asyncio.gather(
            base_workspace_function.aclose(),
            airlock_function.aclose(),
        )


@pytest.fixture(scope="session")
async def setup_test_base_workspace(worker_id, tmp_path_factory, verify) -> AsyncGenerator[Tuple[str, str], None]:
    # Set up
    base_workspace_function = setup_test_base_workspace_with_locks(worker_id, tmp_path_factory, verify)
    base_result = await base_workspace_function.__anext__()
    try:
        yield base_result
    finally:
        await base_workspace_function.aclose()


async def setup_test_airlock_import_review_workspace_and_guacamole_service(verify) -> AsyncGenerator[Tuple[str, str, str, str, str], None]:
    pre_created_workspace_id = config.TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_ID
    # Set up
    workspace_path, workspace_id = await create_or_get_test_workspace(auth_type="Automatic", verify=verify, template_name=resource_strings.AIRLOCK_IMPORT_REVIEW_WORKSPACE, pre_created_workspace_id=pre_created_workspace_id)

    admin_token = await get_admin_token(verify=verify)
    workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)
    pre_created_workspace_service_id = config.TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_SERVICE_ID

    workspace_service_path, workspace_service_id = await create_or_get_test_workpace_service(
        workspace_path,
        workspace_owner_token=workspace_owner_token,
        pre_created_workspace_service_id=pre_created_workspace_service_id,
        verify=verify)

    yield workspace_path, workspace_id, workspace_service_path, workspace_service_id

    # Tear-down in a cascaded way
    await clean_up_test_workspace(pre_created_workspace_id=pre_created_workspace_id, workspace_path=workspace_path, verify=verify)


async def get_workspace_owner_token(workspace_id, verify):
    admin_token = await get_admin_token(verify)
    workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)
    return workspace_owner_token


async def disable_and_delete_ws_resource(resource_path, workspace_id, verify):
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)
    await disable_and_delete_resource(f'/api{resource_path}', workspace_owner_token, verify)


async def disable_and_delete_tre_resource(resource_path, verify):
    admin_token = await get_admin_token(verify)
    await disable_and_delete_resource(f'/api{resource_path}', admin_token, verify)
