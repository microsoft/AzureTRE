import pytest

from e2e_tests.conftest import get_workspace_owner_token, disable_and_delete_ws_resource
from helpers import check_aad_auth_redirect
from resources.resource import get_resource, post_resource
from resources import strings

pytestmark = pytest.mark.asyncio(loop_scope="session")

workspace_services = [
    strings.AZUREML_SERVICE,
    strings.GITEA_SERVICE,
    strings.MLFLOW_SERVICE,
    strings.MYSQL_SERVICE,
    strings.HEALTH_SERVICE,
    strings.AZURESQL_SERVICE,
    strings.OPENAI_SERVICE
]


@pytest.mark.extended
@pytest.mark.timeout(75 * 60)
async def test_create_guacamole_service_into_base_workspace(setup_test_workspace_and_guacamole_service, verify) -> None:
    _, workspace_id, workspace_service_path, _ = setup_test_workspace_and_guacamole_service
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    await ping_guacamole_workspace_service(workspace_service_path, workspace_owner_token, verify)

    user_resource_payload = {
        "templateName": strings.GUACAMOLE_WINDOWS_USER_RESOURCE,
        "properties": {
            "display_name": "My VM",
            "description": "Will be using this VM for my research",
            "os_image": "Windows 11",
            "admin_username": "researcher",
            "install_azure_cli": False,
            "install_vscode": False,
            "install_storage_explorer": False,
            "install_git": False,
            "install_python_tools": False,
            "install_r_tools": False
        }
    }

    _, _ = await post_resource(user_resource_payload, f'/api{workspace_service_path}/{strings.API_USER_RESOURCES}', workspace_owner_token, verify, method="POST")


@pytest.mark.extended_aad
@pytest.mark.timeout(75 * 60)
async def test_create_guacamole_service_into_aad_workspace(setup_test_aad_workspace, verify) -> None:
    """This test will create a Guacamole service but will create a workspace and automatically register the AAD Application"""
    workspace_path, workspace_id = setup_test_aad_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    workspace_service_payload = {
        "templateName": strings.GUACAMOLE_SERVICE,
        "properties": {
            "display_name": "Workspace service test",
            "description": "Workspace service for E2E test"
        }
    }

    workspace_service_path, _ = await post_resource(workspace_service_payload, f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}', workspace_owner_token, verify)

    await ping_guacamole_workspace_service(workspace_service_path, workspace_owner_token, verify)


async def ping_guacamole_workspace_service(workspace_service_path, access_token, verify) -> None:
    workspace_service = await get_resource(f"/api{workspace_service_path}", access_token, verify)
    endpoint = workspace_service["workspaceService"]["properties"]["admin_connection_uri"]
    await check_aad_auth_redirect(endpoint, verify)


@pytest.mark.workspace_services
@pytest.mark.timeout(45 * 60)
@pytest.mark.parametrize("template_name", workspace_services)
async def test_install_workspace_service(template_name, verify, setup_test_workspace) -> None:
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    service_payload = {
        "templateName": template_name,
        "properties": {
            "display_name": f"{template_name} test",
            "description": "Workspace service for E2E test"
        }
    }

    workspace_service_path, _ = await post_resource(service_payload, f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}', workspace_owner_token, verify)

    await disable_and_delete_ws_resource(workspace_service_path, workspace_id, verify)


@pytest.mark.workspace_services
@pytest.mark.extended_aad
@pytest.mark.foundry
@pytest.mark.timeout(75 * 60)
async def test_ai_foundry_model_service_lifecycle(verify, setup_test_foundry_workspace) -> None:
    workspace_path, workspace_id = setup_test_foundry_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)
    workspace_service_path, _ = await post_resource(
        {
            "templateName": strings.AI_FOUNDRY_SERVICE,
            "properties": {
                "display_name": "Private Foundry model test",
                "description": "Model-only service lifecycle",
                "openai_model_capacity": 1
            }
        },
        f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}',
        workspace_owner_token,
        verify
    )
    try:
        service = await get_resource(f"/api{workspace_service_path}", workspace_owner_token, verify)
        properties = service["workspaceService"]["properties"]
        assert properties["ai_foundry_id"].startswith("/subscriptions/")
        assert properties["openai_model"] == "gpt-5.1 | 2025-11-13"
        assert properties["openai_model_capacity"] == 1
        assert properties["is_exposed_externally"] is False
        assert properties["local_auth_enabled"] is False
        assert properties["openai_endpoint"].startswith("https://")
        assert properties["openai_model_deployment"]
        assert properties["openai_api_key_secret_id"] == ""

        # Exercise the upgrade action without opening public access or enabling keys.
        workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)
        await post_resource(
            {"properties": {"openai_model_capacity": 1}},
            f"/api{workspace_service_path}", workspace_owner_token, verify, method="PATCH")
        updated = await get_resource(f"/api{workspace_service_path}", workspace_owner_token, verify)
        updated_properties = updated["workspaceService"]["properties"]
        assert updated_properties["ai_foundry_id"] == properties["ai_foundry_id"]
        assert updated_properties["openai_endpoint"] == properties["openai_endpoint"]
        assert updated_properties["openai_model_deployment"] == properties["openai_model_deployment"]
        assert updated_properties["is_exposed_externally"] is False
        assert updated_properties["local_auth_enabled"] is False
        assert updated_properties["openai_api_key_secret_id"] == ""
    finally:
        await disable_and_delete_ws_resource(workspace_service_path, workspace_id, verify)
