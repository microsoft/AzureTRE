import datetime
from unittest.mock import AsyncMock
import uuid
import pytest
import pytest_asyncio
from mock import patch
import json

from fastapi import HTTPException, status

from api.routes.resource_helpers import save_and_deploy_resource, send_uninstall_message, mask_sensitive_properties, enrich_resource_with_available_upgrades
from db.repositories.resources_history import ResourceHistoryRepository
from tests_ma.test_api.conftest import create_test_user
from resources import strings

from db.repositories.resources import ResourceRepository
from db.repositories.operations import OperationRepository
from models.domain.operation import Status, Operation, OperationStep
from models.domain.resource import AvailableUpgrade, RequestAction, ResourceType
from models.domain.workspace import Workspace


WORKSPACE_ID = '933ad738-7265-4b5f-9eae-a1a62928772e'
FAKE_CREATE_TIME = datetime.datetime(2021, 1, 1, 17, 5, 55)
FAKE_CREATE_TIMESTAMP: float = FAKE_CREATE_TIME.timestamp()
FAKE_UPDATE_TIME = datetime.datetime(2022, 1, 1, 17, 5, 55)
FAKE_UPDATE_TIMESTAMP: float = FAKE_UPDATE_TIME.timestamp()


@pytest_asyncio.fixture
async def resource_repo() -> ResourceRepository:
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=AsyncMock()):
        resource_repo_mock = await ResourceRepository().create()
        yield resource_repo_mock


@pytest_asyncio.fixture
async def operations_repo() -> OperationRepository:
    operation_repo_mock = await OperationRepository().create()
    yield operation_repo_mock


@pytest_asyncio.fixture
async def resource_history_repo() -> ResourceHistoryRepository:
    resource_history_repo_mock = await ResourceHistoryRepository().create()
    yield resource_history_repo_mock


def sample_resource(workspace_id=WORKSPACE_ID):
    return Workspace(
        id=workspace_id,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={
            "client_id": "12345"
        },
        resourcePath=f'/workspaces/{workspace_id}',
        user=create_test_user(),
        updatedWhen=FAKE_CREATE_TIMESTAMP
    )


def sample_resource_with_secret():
    return Workspace(
        id=WORKSPACE_ID,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={
            "client_id": "12345",
            "secret": "iamsecret",
            "prop_with_nested_secret": {
                "nested_secret": "iamanestedsecret"
            }
        },
        resourcePath=f'/workspaces/{WORKSPACE_ID}',
        user=create_test_user(),
        updatedWhen=FAKE_CREATE_TIMESTAMP
    )


def sample_resource_operation(resource_id: str, operation_id: str):
    operation = Operation(
        id=operation_id,
        resourceId=resource_id,
        resourcePath=f'/workspaces/{resource_id}',
        resourceVersion=0,
        action="install",
        message="test",
        Status=Status.Deployed,
        createdWhen=FAKE_CREATE_TIMESTAMP,
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_test_user(),
        steps=[
            OperationStep(
                id="random-uuid-1",
                templateStepId="main",
                stepTitle="Main step for resource-id",
                resourceAction="install",
                resourceType=ResourceType.Workspace,
                resourceTemplateName="template1",
                resourceId=resource_id,
                updatedWhen=FAKE_CREATE_TIMESTAMP,
                sourceTemplateResourceId=resource_id
            )
        ]
    )
    return operation


class TestResourceHelpers:
    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message")
    @pytest.mark.asyncio
    async def test_save_and_deploy_resource_saves_item(self, _, resource_template_repo, resource_repo, operations_repo, basic_resource_template, resource_history_repo):
        resource = sample_resource()
        operation = sample_resource_operation(resource_id=resource.id, operation_id=str(uuid.uuid4()))

        resource_repo.save_item = AsyncMock(return_value=None)
        operations_repo.create_operation_item = AsyncMock(return_value=operation)

        await save_and_deploy_resource(
            resource=resource,
            resource_repo=resource_repo,
            operations_repo=operations_repo,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            user=create_test_user(),
            resource_template=basic_resource_template)

        resource_repo.save_item.assert_called_once_with(resource)

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @pytest.mark.asyncio
    async def test_save_and_deploy_resource_raises_503_if_save_to_db_fails(self, resource_template_repo, resource_repo, operations_repo, basic_resource_template, resource_history_repo):
        resource = sample_resource()
        resource_repo.save_item = AsyncMock(side_effect=Exception)

        with pytest.raises(HTTPException) as ex:
            await save_and_deploy_resource(
                resource=resource,
                resource_repo=resource_repo,
                operations_repo=operations_repo,
                resource_template_repo=resource_template_repo,
                resource_history_repo=resource_history_repo,
                user=create_test_user(),
                resource_template=basic_resource_template)

        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=None)
    @pytest.mark.asyncio
    async def test_save_and_deploy_resource_sends_resource_request_message(self, send_resource_request_mock, resource_template_repo, resource_repo, operations_repo, basic_resource_template, resource_history_repo):
        resource = sample_resource()
        operation = sample_resource_operation(resource_id=resource.id, operation_id=str(uuid.uuid4()))

        resource_repo.save_item = AsyncMock(return_value=None)
        operations_repo.create_operations_item = AsyncMock(return_value=operation)

        user = create_test_user()
        await save_and_deploy_resource(
            resource=resource,
            resource_repo=resource_repo,
            operations_repo=operations_repo,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            user=create_test_user(),
            resource_template=basic_resource_template)

        send_resource_request_mock.assert_called_once_with(
            resource=resource,
            operations_repo=operations_repo,
            resource_repo=resource_repo,
            user=user,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            action=RequestAction.Install)

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message", side_effect=Exception)
    @pytest.mark.asyncio
    async def test_save_and_deploy_resource_raises_503_if_send_request_fails(self, _, resource_template_repo, resource_repo, operations_repo, basic_resource_template, resource_history_repo):
        resource = sample_resource()
        resource_repo.save_item = AsyncMock(return_value=None)
        resource_repo.delete_item = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as ex:
            await save_and_deploy_resource(
                resource=resource,
                resource_repo=resource_repo,
                operations_repo=operations_repo,
                resource_template_repo=resource_template_repo,
                resource_history_repo=resource_history_repo,
                user=create_test_user(),
                resource_template=basic_resource_template)

        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message", side_effect=Exception)
    @pytest.mark.asyncio
    async def test_save_and_deploy_resource_deletes_item_from_db_if_send_request_fails(self, _, resource_template_repo, resource_repo, operations_repo, basic_resource_template, resource_history_repo):
        resource = sample_resource()

        resource_repo.save_item = AsyncMock(return_value=None)
        resource_repo.delete_item = AsyncMock(return_value=None)
        operations_repo.create_operation_item = AsyncMock(return_value=None)

        with pytest.raises(HTTPException):
            await save_and_deploy_resource(
                resource=resource,
                resource_repo=resource_repo,
                operations_repo=operations_repo,
                resource_template_repo=resource_template_repo,
                resource_history_repo=resource_history_repo,
                user=create_test_user(),
                resource_template=basic_resource_template)

        resource_repo.delete_item.assert_called_once_with(resource.id)

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=None)
    @patch("api.routes.workspaces.OperationRepository")
    @pytest.mark.asyncio
    async def test_send_uninstall_message_sends_uninstall_message(self, operations_repo, send_request_mock, resource_template_repo, resource_repo, resource_history_repo):
        resource = sample_resource()
        user = create_test_user()

        await send_uninstall_message(
            resource=resource,
            resource_repo=resource_repo,
            operations_repo=operations_repo,
            resource_type=ResourceType.Workspace,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            user=user)

        send_request_mock.assert_called_once_with(
            resource=resource,
            operations_repo=operations_repo,
            resource_repo=resource_repo,
            user=user,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            action=RequestAction.UnInstall,
            is_cascade=False)

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("api.routes.resource_helpers.send_resource_request_message", side_effect=Exception)
    @patch("api.routes.workspaces.OperationRepository")
    @pytest.mark.asyncio
    async def test_send_uninstall_message_raises_503_on_service_bus_exception(self, operations_repo, _, resource_template_repo, resource_repo, basic_resource_template, resource_history_repo):
        with pytest.raises(HTTPException) as ex:
            await send_uninstall_message(
                resource=sample_resource(),
                resource_repo=resource_repo,
                operations_repo=operations_repo,
                resource_type=ResourceType.Workspace,
                resource_template_repo=resource_template_repo,
                resource_history_repo=resource_history_repo,
                user=create_test_user())

        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @patch("service_bus.resource_request_sender.send_deployment_message")
    @pytest.mark.asyncio
    async def test_save_and_deploy_masks_secrets(self, send_deployment_message_mock, resource_template_repo, resource_repo, operations_repo, basic_resource_template, resource_history_repo):
        resource = sample_resource_with_secret()
        step_id = "random-uuid-1"
        operation_id = str(uuid.uuid4())
        operation = sample_resource_operation(resource_id=resource.id, operation_id=operation_id)

        resource_repo.save_item = AsyncMock(return_value=None)
        resource_repo.get_resource_by_id = AsyncMock(return_value=resource)
        operations_repo.create_operation_item = AsyncMock(return_value=operation)

        resource_template_repo.get_template_by_name_and_version = AsyncMock(return_value=basic_resource_template)

        user = create_test_user()

        await save_and_deploy_resource(
            resource=resource,
            resource_repo=resource_repo,
            operations_repo=operations_repo,
            resource_template_repo=resource_template_repo,
            resource_history_repo=resource_history_repo,
            user=user,
            resource_template=basic_resource_template)

        # Checking that the resource sent to ServiceBus was the same as the one created
        send_deployment_message_mock.assert_called_once_with(
            content=json.dumps(resource.get_resource_request_message_payload(operation_id=operation_id, step_id=step_id, action="install")),
            correlation_id=operation_id,
            session_id=resource.id,
            action="install")

        # Checking that the item saved had a secret redacted
        resource.properties["secret"] = strings.REDACTED_SENSITIVE_VALUE
        resource.properties["prop_with_nested_secret"]["nested_secret"] = strings.REDACTED_SENSITIVE_VALUE

        resource_repo.save_item.assert_called_once_with(resource)

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @pytest.mark.asyncio
    async def test_enrich_resource_with_available_upgrades_when_there_are_new_upgrades_returns_relevant_upgrades_only(self, resource_template_repo):
        resource_template_repo.get_all_template_versions = AsyncMock(return_value=['0.1.0', '0.1.2', '1.0.0', '1.0.1'])
        resource = sample_resource()
        await enrich_resource_with_available_upgrades(resource, resource_template_repo)

        assert resource.availableUpgrades == [AvailableUpgrade(version='0.1.2', forceUpdateRequired=False),
                                              AvailableUpgrade(version='1.0.0', forceUpdateRequired=True),
                                              AvailableUpgrade(version='1.0.1', forceUpdateRequired=True)]

    @patch("api.routes.workspaces.ResourceTemplateRepository")
    @pytest.mark.asyncio
    async def test_enrich_resource_with_available_upgrades_when_there_are_no_upgrades_returns_empty_list(self, resource_template_repo):
        resource_template_repo.get_all_template_versions = AsyncMock(return_value=['0.1.0'])
        resource = sample_resource()
        await enrich_resource_with_available_upgrades(resource, resource_template_repo)
        assert resource.availableUpgrades == []

    def test_sensitive_properties_get_masked(self, basic_resource_template):
        resource = sample_resource_with_secret()

        properties = resource.properties
        masked_resource = mask_sensitive_properties(properties, basic_resource_template)
        assert masked_resource["client_id"] == "12345"
        assert masked_resource["secret"] == strings.REDACTED_SENSITIVE_VALUE
        assert masked_resource["prop_with_nested_secret"]["nested_secret"] == strings.REDACTED_SENSITIVE_VALUE
