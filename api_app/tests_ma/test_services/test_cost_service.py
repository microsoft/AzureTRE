from unittest.mock import AsyncMock
from mock import patch
import pytest
from models.domain.costs import GranularityEnum
from models.domain.shared_service import SharedService, ResourceType
from models.domain.user_resource import UserResource
from models.domain.workspace import Workspace
from models.domain.workspace_service import WorkspaceService
from services.cost_service import CostService, SubscriptionNotSupported
from datetime import date, datetime, timedelta
from azure.mgmt.costmanagement.models import QueryResult, TimeframeType, QueryDefinition, QueryColumn
from azure.core.exceptions import ResourceNotFoundError

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def clear_lru_cache():
    CostService.cache_clear()
    yield
    CostService.cache_clear()


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
# CostService is lru_cached which creates a wrapper method
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_query_tre_costs_with_granularity_none_returns_correct_cost_report(get_resource_groups_by_tag_mock, client_mock,
                                                                                 shared_service_repo_mock, workspace_repo_mock):
    client_mock.return_value.query.usage.return_value = __get_cost_management_query_result()
    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_get_active_workspaces_return_value(workspace_repo_mock)
    __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock)

    cost_service = CostService()
    cost_report = await cost_service.query_tre_costs(
        "guy22", GranularityEnum.none, datetime.now(), datetime.now(), workspace_repo_mock, shared_service_repo_mock)

    assert len(cost_report.core_services) == 1
    assert cost_report.core_services[0].cost == 37.6
    assert cost_report.core_services[0].date is None
    assert len(cost_report.shared_services) == 2
    assert cost_report.shared_services[0].id == "848e8eb5-0df6-4d0f-9162-afd9a3fa0631"
    assert cost_report.shared_services[0].name == "Shared service tre-shared-service-firewall"
    assert len(cost_report.shared_services[0].costs) == 1
    assert cost_report.shared_services[0].costs[0].cost == 6.8
    assert cost_report.shared_services[1].id == "f16d0324-9027-4448-b69b-2d48d925e6c0"
    assert cost_report.shared_services[1].name == "Shared service tre-shared-service-gitea"
    assert len(cost_report.shared_services[1].costs) == 1
    assert cost_report.shared_services[1].costs[0].cost == 4.8
    assert len(cost_report.workspaces) == 2
    assert cost_report.workspaces[0].id == "19b7ce24-aa35-438c-adf6-37e6762911a6"
    assert cost_report.workspaces[0].name == "the workspace display name1"
    assert len(cost_report.workspaces[0].costs) == 1
    assert cost_report.workspaces[0].costs[0].cost == 1.8
    assert cost_report.workspaces[1].id == "d680d6b7-d1d9-411c-9101-0793da980c81"
    assert cost_report.workspaces[1].name == "the workspace display name2"
    assert len(cost_report.workspaces[1].costs) == 2
    assert cost_report.workspaces[1].costs[0].cost == 5.8
    assert cost_report.workspaces[1].costs[0].currency == "ILS"
    assert cost_report.workspaces[1].costs[1].cost == 2.8
    assert cost_report.workspaces[1].costs[1].currency == "USD"


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
# CostService is lru_cached which creates a wrapper method
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_query_tre_costs_with_granularity_daily_returns_correct_cost_report(
        get_resource_groups_by_tag_mock, client_mock, shared_service_repo_mock, workspace_repo_mock):
    client_mock.return_value.query.usage.return_value = __set_cost_management_client_mock_query_result()
    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_get_active_workspaces_return_value(workspace_repo_mock)
    __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock)

    cost_service = CostService()
    cost_report = await cost_service.query_tre_costs(
        "guy22", GranularityEnum.daily, datetime.now(), datetime.now(), workspace_repo_mock, shared_service_repo_mock)

    assert len(cost_report.core_services) == 3
    assert cost_report.core_services[0].cost == 31.6
    assert cost_report.core_services[0].date == date(2022, 5, 1)
    assert len(cost_report.shared_services) == 2
    assert cost_report.shared_services[0].id == "848e8eb5-0df6-4d0f-9162-afd9a3fa0631"
    assert cost_report.shared_services[0].name == "Shared service tre-shared-service-firewall"
    assert len(cost_report.shared_services[0].costs) == 3
    assert cost_report.shared_services[0].costs[0].cost == 3.8
    assert cost_report.shared_services[0].costs[0].date == date(2022, 5, 1)
    assert cost_report.shared_services[0].costs[1].cost == 4.8
    assert cost_report.shared_services[0].costs[1].date == date(2022, 5, 2)
    assert cost_report.shared_services[0].costs[2].cost == 5.8
    assert cost_report.shared_services[0].costs[2].date == date(2022, 5, 3)
    assert cost_report.shared_services[1].id == "f16d0324-9027-4448-b69b-2d48d925e6c0"
    assert cost_report.shared_services[1].name == "Shared service tre-shared-service-gitea"
    assert len(cost_report.shared_services[1].costs) == 3
    assert cost_report.shared_services[1].costs[0].cost == 2.8
    assert cost_report.shared_services[1].costs[0].date == date(2022, 5, 1)
    assert cost_report.shared_services[1].costs[1].cost == 3.8
    assert cost_report.shared_services[1].costs[1].date == date(2022, 5, 2)
    assert cost_report.shared_services[1].costs[2].cost == 4.8
    assert cost_report.shared_services[1].costs[2].date == date(2022, 5, 3)
    assert len(cost_report.workspaces) == 2
    assert cost_report.workspaces[0].id == "19b7ce24-aa35-438c-adf6-37e6762911a6"
    assert cost_report.workspaces[0].name == "the workspace display name1"
    assert len(cost_report.workspaces[0].costs) == 3
    assert cost_report.workspaces[0].costs[0].cost == 1.8
    assert cost_report.workspaces[0].costs[0].date == date(2022, 5, 1)
    assert cost_report.workspaces[0].costs[1].cost == 2.8
    assert cost_report.workspaces[0].costs[1].date == date(2022, 5, 2)
    assert cost_report.workspaces[0].costs[2].cost == 3.8
    assert cost_report.workspaces[0].costs[2].date == date(2022, 5, 3)
    assert cost_report.workspaces[1].id == "d680d6b7-d1d9-411c-9101-0793da980c81"
    assert cost_report.workspaces[1].name == "the workspace display name2"
    assert len(cost_report.workspaces[1].costs) == 4
    assert cost_report.workspaces[1].costs[0].cost == 4.8
    assert cost_report.workspaces[1].costs[0].date == date(2022, 5, 1)
    assert cost_report.workspaces[1].costs[1].cost == 5.8
    assert cost_report.workspaces[1].costs[1].date == date(2022, 5, 2)
    assert cost_report.workspaces[1].costs[2].cost == 16.8
    assert cost_report.workspaces[1].costs[2].date == date(2022, 5, 3)
    assert cost_report.workspaces[1].costs[2].currency == "ILS"
    assert cost_report.workspaces[1].costs[3].cost == 6.8
    assert cost_report.workspaces[1].costs[3].date == date(2022, 5, 3)
    assert cost_report.workspaces[1].costs[3].currency == "USD"


def __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock):
    get_resource_groups_by_tag_mock.return_value = {
        'rg-guy22': '"tre_id":"guy22"',
        'rg-guy22-ws-11a6': '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"',
        'rg-guy22-ws-0c81': '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"'
    }


def __get_daily_cost_management_query_result():
    query_result = QueryResult()
    query_result.rows = [
        [31.6, 20220501, '"tre_core_service_id":"guy22"', 'USD'],
        [32.6, 20220502, '"tre_core_service_id":"guy22"', 'USD'],
        [33.6, 20220503, '"tre_core_service_id":"guy22"', 'USD'],

        [44.5, 20220501, '"tre_id":"guy22"', 'USD'],
        [44.5, 20220502, '"tre_id":"guy22"', 'USD'],
        [44.5, 20220503, '"tre_id":"guy22"', 'USD'],
        [12.5, 20220503, '"tre_id":"guy22"', 'ILS'],

        [3.8, 20220501, '"tre_shared_service_id":"848e8eb5-0df6-4d0f-9162-afd9a3fa0631"', 'USD'],
        [4.8, 20220502, '"tre_shared_service_id":"848e8eb5-0df6-4d0f-9162-afd9a3fa0631"', 'USD'],
        [5.8, 20220503, '"tre_shared_service_id":"848e8eb5-0df6-4d0f-9162-afd9a3fa0631"', 'USD'],

        [2.8, 20220501, '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'USD'],
        [3.8, 20220502, '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'USD'],
        [4.8, 20220503, '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'USD'],

        [1.8, 20220501, '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"', 'USD'],
        [2.8, 20220502, '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"', 'USD'],
        [3.8, 20220503, '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"', 'USD'],

        [4.8, 20220501, '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'USD'],
        [5.8, 20220502, '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'USD'],
        [6.8, 20220503, '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'USD'],
    ]
    return query_result


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
# CostService is lru_cached which creates a wrapper method
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_query_tre_costs_with_granularity_none_and_missing_costs_data_returns_empty_cost_report(get_resource_groups_by_tag_mock,
                                                                                                      client_mock,
                                                                                                      shared_service_repo_mock,
                                                                                                      workspace_repo_mock):
    query_result = QueryResult()
    query_result.rows = [
    ]
    query_result.columns = [QueryColumn(name="PreTaxCost", type="Number"),
                            QueryColumn(name="ResourceGroup", type="String"),
                            QueryColumn(name="Tag", type="String"),
                            QueryColumn(name="Currency", type="String")]

    client_mock.return_value.query.usage.return_value = query_result

    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_get_active_workspaces_return_value(workspace_repo_mock)
    __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock)

    cost_service = CostService()
    cost_report = await cost_service.query_tre_costs(
        "guy22", GranularityEnum.none, datetime.now(), datetime.now(), workspace_repo_mock, shared_service_repo_mock)

    assert len(cost_report.core_services) == 0
    assert len(cost_report.shared_services) == 2
    assert len(cost_report.shared_services[0].costs) == 0
    assert len(cost_report.shared_services[1].costs) == 0
    assert len(cost_report.workspaces) == 2
    assert len(cost_report.workspaces[0].costs) == 0
    assert len(cost_report.workspaces[1].costs) == 0


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
# CostService is lru_cached which creates a wrapper method
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_query_tre_costs_for_unsupported_subscription_raises_subscription_not_supported_exception(get_resource_groups_by_tag_mock,
                                                                                                        client_mock,
                                                                                                        shared_service_repo_mock,
                                                                                                        workspace_repo_mock):

    client_mock.return_value.query.usage.side_effect = ResourceNotFoundError({
        "error": {
            "code": "NotFound",
            "message": "Given subscription xxx doesn't have valid WebDirect/AIRS offer type. (Request ID: 12daa3b6-8a53-4759-97ba-511ece1ac95b)"
        }
    })

    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_get_active_workspaces_return_value(workspace_repo_mock)
    __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock)

    cost_service = CostService()

    with pytest.raises(SubscriptionNotSupported):
        await cost_service.query_tre_costs(
            "guy22", GranularityEnum.none, datetime.now(), datetime.now(), workspace_repo_mock, shared_service_repo_mock)


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
# CostService is lru_cached which creates a wrapper method
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_query_tre_costs_with_granularity_daily_and_missing_costs_data_returns_empty_cost_report(get_resource_groups_by_tag_mock,
                                                                                                       client_mock,
                                                                                                       shared_service_repo_mock,
                                                                                                       workspace_repo_mock):
    query_result = QueryResult()
    query_result.rows = [
    ]

    query_result.columns = [QueryColumn(name="PreTaxCost", type="Number"),
                            QueryColumn(name="UsageDate", type="DateTime"),
                            QueryColumn(name="ResourceGroup", type="String"),
                            QueryColumn(name="Tag", type="String"),
                            QueryColumn(name="Currency", type="String")]

    client_mock.return_value.query.usage.return_value = query_result

    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_get_active_workspaces_return_value(workspace_repo_mock)
    __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock)

    cost_service = CostService()
    cost_report = await cost_service.query_tre_costs(
        "guy22", GranularityEnum.daily, datetime.now(), datetime.now(), workspace_repo_mock, shared_service_repo_mock)

    assert len(cost_report.core_services) == 0
    assert len(cost_report.shared_services) == 2
    assert len(cost_report.shared_services[0].costs) == 0
    assert len(cost_report.shared_services[1].costs) == 0
    assert len(cost_report.workspaces) == 2
    assert len(cost_report.workspaces[0].costs) == 0
    assert len(cost_report.workspaces[1].costs) == 0


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
# CostService is lru_cached which creates a wrapper method
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_query_tre_costs_with_granularity_none_and_display_name_data_returns_template_name_in_cost_report(get_resource_groups_by_tag_mock,
                                                                                                                client_mock,
                                                                                                                shared_service_repo_mock,
                                                                                                                workspace_repo_mock):
    client_mock.return_value.query.usage.return_value = __get_cost_management_query_result()
    __set_shared_service_repo_mock_return_value_without_display_name(shared_service_repo_mock)
    __set_workspace_repo_mock_get_active_workspaces_return_value_without_display_name(workspace_repo_mock)
    __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock)

    cost_service = CostService()
    cost_report = await cost_service.query_tre_costs(
        "guy22", GranularityEnum.none, datetime.now(), datetime.now(), workspace_repo_mock, shared_service_repo_mock)

    assert len(cost_report.core_services) == 1
    assert cost_report.core_services[0].cost == 37.6
    assert cost_report.core_services[0].date is None
    assert len(cost_report.shared_services) == 2
    assert cost_report.shared_services[0].id == "848e8eb5-0df6-4d0f-9162-afd9a3fa0631"
    assert cost_report.shared_services[0].name == "tre-shared-service-firewall"
    assert len(cost_report.shared_services[0].costs) == 1
    assert cost_report.shared_services[0].costs[0].cost == 6.8
    assert cost_report.shared_services[1].id == "f16d0324-9027-4448-b69b-2d48d925e6c0"
    assert cost_report.shared_services[1].name == "tre-shared-service-gitea"
    assert len(cost_report.shared_services[1].costs) == 1
    assert cost_report.shared_services[1].costs[0].cost == 4.8
    assert len(cost_report.workspaces) == 2
    assert cost_report.workspaces[0].id == "19b7ce24-aa35-438c-adf6-37e6762911a6"
    assert cost_report.workspaces[0].name == "tre-workspace-base"
    assert len(cost_report.workspaces[0].costs) == 1
    assert cost_report.workspaces[0].costs[0].cost == 1.8
    assert cost_report.workspaces[1].id == "d680d6b7-d1d9-411c-9101-0793da980c81"
    assert cost_report.workspaces[1].name == "tre-workspace-base"
    assert cost_report.workspaces[1].costs[0].cost == 5.8
    assert cost_report.workspaces[1].costs[0].currency == "ILS"
    assert cost_report.workspaces[1].costs[1].cost == 2.8
    assert cost_report.workspaces[1].costs[1].currency == "USD"


@pytest.mark.parametrize("from_date,to_date", [(None, datetime.now()), (datetime.now(), None), (None, None)])
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
# CostService is lru_cached which creates a wrapper method
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_query_tre_costs_with_dates_set_as_none_calls_client_with_month_to_date(get_resource_groups_by_tag_mock,
                                                                                      client_mock, shared_service_repo_mock,
                                                                                      workspace_repo_mock, from_date,
                                                                                      to_date):
    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_get_active_workspaces_return_value(workspace_repo_mock)
    __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock)

    cost_service = CostService()
    CostService.cache_clear()
    await cost_service.query_tre_costs(
        "guy22", GranularityEnum.none, from_date, to_date, workspace_repo_mock, shared_service_repo_mock)

    query_definition: QueryDefinition = client_mock.return_value.query.usage.call_args_list[0][0][1]
    assert query_definition.timeframe == TimeframeType.MONTH_TO_DATE


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
# CostService is lru_cached which creates a wrapper method
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_query_tre_costs_with_dates_set_as_none_calls_client_with_custom_dates(get_resource_groups_by_tag_mock,
                                                                                     client_mock, shared_service_repo_mock,
                                                                                     workspace_repo_mock):
    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_get_active_workspaces_return_value(workspace_repo_mock)
    __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock)

    from_date = datetime.now() - timedelta(days=10)
    to_date = datetime.now()

    cost_service = CostService()
    await cost_service.query_tre_costs(
        "guy22", GranularityEnum.none, from_date, to_date, workspace_repo_mock, shared_service_repo_mock)

    query_definition: QueryDefinition = client_mock.return_value.query.usage.call_args_list[0][0][1]
    assert query_definition.timeframe == TimeframeType.CUSTOM
    assert query_definition.time_period.from_property == from_date
    assert query_definition.time_period.to == to_date


def __set_workspace_repo_mock_get_active_workspaces_return_value(workspace_repo_mock):
    workspace_repo_mock.get_active_workspaces = AsyncMock(return_value=[
        Workspace(id='19b7ce24-aa35-438c-adf6-37e6762911a6', templateName='tre-workspace-base',
                  resourceType=ResourceType.Workspace, templateVersion="1", _etag="x",
                  properties={'display_name': 'the workspace display name1'}),
        Workspace(id='d680d6b7-d1d9-411c-9101-0793da980c81', templateName='tre-workspace-base',
                  resourceType=ResourceType.Workspace, templateVersion="1", _etag="x",
                  properties={'display_name': 'the workspace display name2'})
    ])


def __set_workspace_repo_mock_get_active_workspaces_return_value_without_display_name(workspace_repo_mock):
    workspace_repo_mock.get_active_workspaces = AsyncMock(return_value=[
        Workspace(id='19b7ce24-aa35-438c-adf6-37e6762911a6', templateName='tre-workspace-base',
                  resourceType=ResourceType.Workspace, templateVersion="1", _etag="x"),
        Workspace(id='d680d6b7-d1d9-411c-9101-0793da980c81', templateName='tre-workspace-base',
                  resourceType=ResourceType.Workspace, templateVersion="1", _etag="x")
    ])


def __set_shared_service_repo_mock_return_value(shared_service_repo_mock):
    shared_service_repo_mock.get_active_shared_services = AsyncMock(return_value=[
        SharedService(id='848e8eb5-0df6-4d0f-9162-afd9a3fa0631', resourceType=ResourceType.SharedService,
                      templateName="tre-shared-service-firewall", templateVersion="1", _etag="x",
                      properties={'display_name': 'Shared service tre-shared-service-firewall'}),
        SharedService(id='f16d0324-9027-4448-b69b-2d48d925e6c0', resourceType=ResourceType.SharedService,
                      templateName="tre-shared-service-gitea", templateVersion="1", _etag="x",
                      properties={'display_name': 'Shared service tre-shared-service-gitea'})
    ])


def __set_shared_service_repo_mock_return_value_without_display_name(shared_service_repo_mock):
    shared_service_repo_mock.get_active_shared_services = AsyncMock(return_value=[
        SharedService(id='848e8eb5-0df6-4d0f-9162-afd9a3fa0631', resourceType=ResourceType.SharedService,
                      templateName="tre-shared-service-firewall", templateVersion="1", _etag="x"),
        SharedService(id='f16d0324-9027-4448-b69b-2d48d925e6c0', resourceType=ResourceType.SharedService,
                      templateName="tre-shared-service-gitea", templateVersion="1", _etag="x")
    ])


def __set_workspace_repo_mock_get_workspace_by_id_return_value(workspace_repo_mock):
    workspace_repo_mock.get_workspace_by_id = AsyncMock(return_value=Workspace(id='19b7ce24-aa35-438c-adf6-37e6762911a6',
                                                                               templateName='tre-workspace-base',
                                                                               resourceType=ResourceType.Workspace,
                                                                               templateVersion="1", _etag="x",
                                                                               properties={
                                                                                  'display_name': "workspace 1"}))


def __set_workspace_service_repo_mock_return_value(workspace_service_repo_mock):
    workspace_service_repo_mock.get_active_workspace_services_for_workspace = AsyncMock(return_value=[
        WorkspaceService(id='f8cac589-c497-4896-9fac-58e65685a20c', resourceType=ResourceType.WorkspaceService,
                         templateName="tre-service-guacamole", templateVersion="1", _etag="x",
                         properties={'display_name': 'Guacamole'}),
        WorkspaceService(id='9ad6e5d8-0bef-4b9f-91d6-ae33884883a1', resourceType=ResourceType.WorkspaceService,
                         templateName="tre-service-azureml", templateVersion="1", _etag="x",
                         properties={'display_name': 'Azure ML'})
    ])


def __set_user_resource_repo_mock_return_value(user_resource_repo_mock):
    # each time 'get_user_resources_for_workspace_service' is called it will return
    # the next sub-array
    user_resource_repo_mock.get_user_resources_for_workspace_service = AsyncMock(side_effect=[
        [
            UserResource(id='09ed3e6e-fee5-41d0-937e-89644575e78c', resourceType=ResourceType.UserResource,
                         templateName="tre-user_resource_guacamole_vm", templateVersion="1", _etag="x",
                         properties={'display_name': 'VM1'}),
            UserResource(id='8ce4a294-95ae-45a9-8d48-6525ce84eb5a', resourceType=ResourceType.UserResource,
                         templateName="tre-user_resource_guacamole_vm", templateVersion="1", _etag="x",
                         properties={'display_name': 'VM2'})
        ],
        [
            UserResource(id='6ede6dc0-a1e1-40bd-92d7-3b3adcbec66d', resourceType=ResourceType.UserResource,
                         templateName="tre-user_resource_compute_instance", templateVersion="1", _etag="x",
                         properties={'display_name': 'Compute Instance 1'}),
            UserResource(id='915760d8-cf09-4cdb-b73b-815e6bfaef6f', resourceType=ResourceType.UserResource,
                         templateName="tre-user_resource_compute_instance", templateVersion="1", _etag="x",
                         properties={'display_name': 'Compute Instance 2'})
        ]

    ])


@pytest.mark.asyncio
@patch('db.repositories.user_resources.UserResourceRepository')
@patch('db.repositories.workspace_services.WorkspaceServiceRepository')
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('services.cost_service.CostManagementClient')
# CostService is lru_cached which creates a wrapper method
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_query_tre_workspace_costs_with_granularity_none_returns_correct_workspace_cost_report(get_resource_groups_by_tag_mock,
                                                                                                     client_mock,
                                                                                                     workspace_repo_mock,
                                                                                                     workspace_services_repo_mock,
                                                                                                     user_resource_repo_mock):
    client_mock.return_value.query.usage.return_value = __get_cost_management_query_result()
    __set_workspace_repo_mock_get_workspace_by_id_return_value(workspace_repo_mock)
    __set_workspace_service_repo_mock_return_value(workspace_services_repo_mock)
    __set_user_resource_repo_mock_return_value(user_resource_repo_mock)
    __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock)

    cost_service = CostService()
    workspace_cost_report = await cost_service.query_tre_workspace_costs(
        "19b7ce24-aa35-438c-adf6-37e6762911a6", GranularityEnum.none, datetime.now(), datetime.now(),
        workspace_repo_mock,
        workspace_services_repo_mock, user_resource_repo_mock)

    assert workspace_cost_report.id == "19b7ce24-aa35-438c-adf6-37e6762911a6"
    assert workspace_cost_report.name == "workspace 1"
    assert len(workspace_cost_report.workspace_services) == 2
    assert workspace_cost_report.workspace_services[0].id == "f8cac589-c497-4896-9fac-58e65685a20c"
    assert workspace_cost_report.workspace_services[0].name == "Guacamole"
    assert len(workspace_cost_report.workspace_services[0].costs) == 1
    assert workspace_cost_report.workspace_services[0].costs[0].cost == 6.6
    assert len(workspace_cost_report.workspace_services[0].user_resources) == 2
    assert workspace_cost_report.workspace_services[0].user_resources[0].id == "09ed3e6e-fee5-41d0-937e-89644575e78c"
    assert workspace_cost_report.workspace_services[0].user_resources[0].name == "VM1"
    assert len(workspace_cost_report.workspace_services[0].user_resources[0].costs) == 1
    assert workspace_cost_report.workspace_services[0].user_resources[0].costs[0].cost == 1.3
    assert workspace_cost_report.workspace_services[0].user_resources[1].id == "8ce4a294-95ae-45a9-8d48-6525ce84eb5a"
    assert workspace_cost_report.workspace_services[0].user_resources[1].name == "VM2"
    assert len(workspace_cost_report.workspace_services[0].user_resources[1].costs) == 1
    assert workspace_cost_report.workspace_services[0].user_resources[1].costs[0].cost == 2.3

    assert workspace_cost_report.workspace_services[1].id == "9ad6e5d8-0bef-4b9f-91d6-ae33884883a1"
    assert workspace_cost_report.workspace_services[1].name == "Azure ML"
    assert len(workspace_cost_report.workspace_services[1].costs) == 1
    assert workspace_cost_report.workspace_services[1].costs[0].cost == 9.3
    assert len(workspace_cost_report.workspace_services[1].user_resources) == 2
    assert workspace_cost_report.workspace_services[1].user_resources[0].id == "6ede6dc0-a1e1-40bd-92d7-3b3adcbec66d"
    assert workspace_cost_report.workspace_services[1].user_resources[0].name == "Compute Instance 1"
    assert len(workspace_cost_report.workspace_services[1].user_resources[0].costs) == 1
    assert workspace_cost_report.workspace_services[1].user_resources[0].costs[0].cost == 5.2
    assert workspace_cost_report.workspace_services[1].user_resources[1].id == "915760d8-cf09-4cdb-b73b-815e6bfaef6f"
    assert workspace_cost_report.workspace_services[1].user_resources[1].name == "Compute Instance 2"
    assert len(workspace_cost_report.workspace_services[1].user_resources[1].costs) == 1
    assert workspace_cost_report.workspace_services[1].user_resources[1].costs[0].cost == 4.1


@pytest.mark.asyncio
@patch('db.repositories.user_resources.UserResourceRepository')
@patch('db.repositories.workspace_services.WorkspaceServiceRepository')
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('services.cost_service.CostManagementClient')
# CostService is lru_cached which creates a wrapper method
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_query_tre_workspace_costs_with_granularity_daily_returns_correct_workspace_cost_report(get_resource_groups_by_tag_mock,
                                                                                                      client_mock,
                                                                                                      workspace_repo_mock,
                                                                                                      workspace_services_repo_mock,
                                                                                                      user_resource_repo_mock):
    client_mock.return_value.query.usage.return_value = __set_cost_management_client_mock_query_result()
    __set_workspace_repo_mock_get_workspace_by_id_return_value(workspace_repo_mock)
    __set_workspace_service_repo_mock_return_value(workspace_services_repo_mock)
    __set_user_resource_repo_mock_return_value(user_resource_repo_mock)
    __set_resource_group_by_tag_return_value(get_resource_groups_by_tag_mock)

    cost_service = CostService()
    workspace_cost_report = await cost_service.query_tre_workspace_costs(
        "19b7ce24-aa35-438c-adf6-37e6762911a6", GranularityEnum.daily, datetime.now(), datetime.now(),
        workspace_repo_mock,
        workspace_services_repo_mock, user_resource_repo_mock)

    assert workspace_cost_report.id == "19b7ce24-aa35-438c-adf6-37e6762911a6"
    assert workspace_cost_report.name == "workspace 1"
    assert len(workspace_cost_report.workspace_services) == 2
    assert workspace_cost_report.workspace_services[0].id == "f8cac589-c497-4896-9fac-58e65685a20c"
    assert workspace_cost_report.workspace_services[0].name == "Guacamole"
    assert len(workspace_cost_report.workspace_services[0].costs) == 3
    assert workspace_cost_report.workspace_services[0].costs[0].cost == 14.8
    assert len(workspace_cost_report.workspace_services[0].user_resources) == 2
    assert workspace_cost_report.workspace_services[0].user_resources[0].id == "09ed3e6e-fee5-41d0-937e-89644575e78c"
    assert workspace_cost_report.workspace_services[0].user_resources[0].name == "VM1"
    assert len(workspace_cost_report.workspace_services[0].user_resources[0].costs) == 4
    assert workspace_cost_report.workspace_services[0].user_resources[0].costs[0].cost == 114.8
    assert workspace_cost_report.workspace_services[0].user_resources[0].costs[1].cost == 115.8
    assert workspace_cost_report.workspace_services[0].user_resources[0].costs[2].cost == 216.8
    assert workspace_cost_report.workspace_services[0].user_resources[0].costs[2].currency == "ILS"
    assert workspace_cost_report.workspace_services[0].user_resources[0].costs[3].cost == 116.8
    assert workspace_cost_report.workspace_services[0].user_resources[0].costs[3].currency == "USD"

    assert workspace_cost_report.workspace_services[0].user_resources[1].id == "8ce4a294-95ae-45a9-8d48-6525ce84eb5a"
    assert workspace_cost_report.workspace_services[0].user_resources[1].name == "VM2"
    assert len(workspace_cost_report.workspace_services[0].user_resources[1].costs) == 3
    assert workspace_cost_report.workspace_services[0].user_resources[1].costs[0].cost == 164.8

    assert workspace_cost_report.workspace_services[1].id == "9ad6e5d8-0bef-4b9f-91d6-ae33884883a1"
    assert workspace_cost_report.workspace_services[1].name == "Azure ML"
    assert len(workspace_cost_report.workspace_services[1].costs) == 3
    assert workspace_cost_report.workspace_services[1].costs[0].cost == 24.8
    assert len(workspace_cost_report.workspace_services[1].user_resources) == 2
    assert workspace_cost_report.workspace_services[1].user_resources[0].id == "6ede6dc0-a1e1-40bd-92d7-3b3adcbec66d"
    assert workspace_cost_report.workspace_services[1].user_resources[0].name == "Compute Instance 1"
    assert len(workspace_cost_report.workspace_services[1].user_resources[0].costs) == 3
    assert workspace_cost_report.workspace_services[1].user_resources[0].costs[0].cost == 164.8
    assert workspace_cost_report.workspace_services[1].user_resources[1].id == "915760d8-cf09-4cdb-b73b-815e6bfaef6f"
    assert workspace_cost_report.workspace_services[1].user_resources[1].name == "Compute Instance 2"
    assert len(workspace_cost_report.workspace_services[1].user_resources[1].costs) == 3
    assert workspace_cost_report.workspace_services[1].user_resources[1].costs[0].cost == 168.8


def __get_cost_management_query_result():
    query_result = QueryResult()
    query_result.rows = [
        [37.6, 'rg-guy22', '"tre_core_service_id":"guy22"', 'USD'],
        [44.5, 'rg-guy22', '"tre_id":"guy22"', 'USD'],
        [6.8, 'rg-guy22', '"tre_shared_service_id":"848e8eb5-0df6-4d0f-9162-afd9a3fa0631"', 'USD'],
        [4.8, 'rg-guy22', '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'USD'],
        [1.8, 'rg-guy22-ws-11a6', '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"', 'USD'],
        [2.8, 'rg-guy22-ws-0c81', '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'USD'],
        [5.8, 'rg-guy22-ws-0c81', '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'ILS'],
        [6.6, 'rg-guy22-ws-11a6', '"tre_workspace_service_id":"f8cac589-c497-4896-9fac-58e65685a20c"', 'USD'],
        [9.3, 'rg-guy22-ws-0c81', '"tre_workspace_service_id":"9ad6e5d8-0bef-4b9f-91d6-ae33884883a1"', 'USD'],
        [1.3, 'rg-guy22-ws-11a6', '"tre_user_resource_id":"09ed3e6e-fee5-41d0-937e-89644575e78c"', 'USD'],
        [2.3, 'rg-guy22-ws-0c81', '"tre_user_resource_id":"8ce4a294-95ae-45a9-8d48-6525ce84eb5a"', 'USD'],
        [5.2, 'rg-guy22-ws-11a6', '"tre_user_resource_id":"6ede6dc0-a1e1-40bd-92d7-3b3adcbec66d"', 'USD'],
        [4.1, 'rg-guy22-ws-11a6', '"tre_user_resource_id":"915760d8-cf09-4cdb-b73b-815e6bfaef6f"', 'USD'],
    ]
    query_result.columns = [QueryColumn(name="PreTaxCost", type="Number"),
                            QueryColumn(name="ResourceGroup", type="String"),
                            QueryColumn(name="Tag", type="String"),
                            QueryColumn(name="Currency", type="String")]
    return query_result


def __set_cost_management_client_mock_query_result():
    query_result = QueryResult()
    query_result.rows = [
        [31.6, 20220501, 'rg-guy22', '"tre_core_service_id":"guy22"', 'USD'],
        [32.6, 20220502, 'rg-guy22', '"tre_core_service_id":"guy22"', 'USD'],
        [33.6, 20220503, 'rg-guy22', '"tre_core_service_id":"guy22"', 'USD'],

        [44.5, 20220501, 'rg-guy22', '"tre_id":"guy22"', 'USD'],
        [44.5, 20220502, 'rg-guy22', '"tre_id":"guy22"', 'USD'],
        [44.5, 20220503, 'rg-guy22', '"tre_id":"guy22"', 'USD'],

        [3.8, 20220501, 'rg-guy22', '"tre_shared_service_id":"848e8eb5-0df6-4d0f-9162-afd9a3fa0631"', 'USD'],
        [4.8, 20220502, 'rg-guy22', '"tre_shared_service_id":"848e8eb5-0df6-4d0f-9162-afd9a3fa0631"', 'USD'],
        [5.8, 20220503, 'rg-guy22', '"tre_shared_service_id":"848e8eb5-0df6-4d0f-9162-afd9a3fa0631"', 'USD'],

        [2.8, 20220501, 'rg-guy22', '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'USD'],
        [3.8, 20220502, 'rg-guy22', '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'USD'],
        [4.8, 20220503, 'rg-guy22', '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'USD'],

        [1.8, 20220501, 'rg-guy22-ws-11a6', '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"', 'USD'],
        [2.8, 20220502, 'rg-guy22-ws-11a6', '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"', 'USD'],
        [3.8, 20220503, 'rg-guy22-ws-11a6', '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"', 'USD'],

        [4.8, 20220501, 'rg-guy22-ws-0c81', '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'USD'],
        [5.8, 20220502, 'rg-guy22-ws-0c81', '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'USD'],
        [6.8, 20220503, 'rg-guy22-ws-0c81', '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'USD'],
        [16.8, 20220503, 'rg-guy22-ws-0c81', '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'ILS'],

        [14.8, 20220501, 'rg-guy22-ws-11a6', '"tre_workspace_service_id":"f8cac589-c497-4896-9fac-58e65685a20c"', 'USD'],
        [15.8, 20220502, 'rg-guy22-ws-11a6', '"tre_workspace_service_id":"f8cac589-c497-4896-9fac-58e65685a20c"', 'USD'],
        [16.8, 20220503, 'rg-guy22-ws-11a6', '"tre_workspace_service_id":"f8cac589-c497-4896-9fac-58e65685a20c"', 'USD'],

        [24.8, 20220501, 'rg-guy22-ws-0c81', '"tre_workspace_service_id":"9ad6e5d8-0bef-4b9f-91d6-ae33884883a1"', 'USD'],
        [25.8, 20220502, 'rg-guy22-ws-0c81', '"tre_workspace_service_id":"9ad6e5d8-0bef-4b9f-91d6-ae33884883a1"', 'USD'],
        [26.8, 20220503, 'rg-guy22-ws-0c81', '"tre_workspace_service_id":"9ad6e5d8-0bef-4b9f-91d6-ae33884883a1"', 'USD'],

        [114.8, 20220501, 'rg-guy22-ws-11a6', '"tre_user_resource_id":"09ed3e6e-fee5-41d0-937e-89644575e78c"', 'USD'],
        [115.8, 20220502, 'rg-guy22-ws-11a6', '"tre_user_resource_id":"09ed3e6e-fee5-41d0-937e-89644575e78c"', 'USD'],
        [116.8, 20220503, 'rg-guy22-ws-11a6', '"tre_user_resource_id":"09ed3e6e-fee5-41d0-937e-89644575e78c"', 'USD'],
        [216.8, 20220503, 'rg-guy22-ws-11a6', '"tre_user_resource_id":"09ed3e6e-fee5-41d0-937e-89644575e78c"', 'ILS'],

        [164.8, 20220501, 'rg-guy22-ws-0c81', '"tre_user_resource_id":"8ce4a294-95ae-45a9-8d48-6525ce84eb5a"', 'USD'],
        [165.8, 20220502, 'rg-guy22-ws-0c81', '"tre_user_resource_id":"8ce4a294-95ae-45a9-8d48-6525ce84eb5a"', 'USD'],
        [166.8, 20220503, 'rg-guy22-ws-0c81', '"tre_user_resource_id":"8ce4a294-95ae-45a9-8d48-6525ce84eb5a"', 'USD'],

        [164.8, 20220501, 'rg-guy22-ws-0c81', '"tre_user_resource_id":"6ede6dc0-a1e1-40bd-92d7-3b3adcbec66d"', 'USD'],
        [165.8, 20220502, 'rg-guy22-ws-0c81', '"tre_user_resource_id":"6ede6dc0-a1e1-40bd-92d7-3b3adcbec66d"', 'USD'],
        [166.8, 20220503, 'rg-guy22-ws-0c81', '"tre_user_resource_id":"6ede6dc0-a1e1-40bd-92d7-3b3adcbec66d"', 'USD'],

        [168.8, 20220501, 'rg-guy22-ws-0c81', '"tre_user_resource_id":"915760d8-cf09-4cdb-b73b-815e6bfaef6f"', 'USD'],
        [168.8, 20220502, 'rg-guy22-ws-0c81', '"tre_user_resource_id":"915760d8-cf09-4cdb-b73b-815e6bfaef6f"', 'USD'],
        [168.8, 20220503, 'rg-guy22-ws-0c81', '"tre_user_resource_id":"915760d8-cf09-4cdb-b73b-815e6bfaef6f"', 'USD']
    ]

    query_result.columns = [QueryColumn(name="PreTaxCost", type="Number"),
                            QueryColumn(name="UsageDate", type="DateTime"),
                            QueryColumn(name="ResourceGroup", type="String"),
                            QueryColumn(name="Tag", type="String"),
                            QueryColumn(name="Currency", type="String")]

    return query_result


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_subscription_id_includes_default_and_workspace_ids(get_resource_groups_by_tag_mock, client_mock, shared_service_repo_mock, workspace_repo_mock):
    from services import cost_service as cs
    cs.config.SUBSCRIPTION_ID = "default-sub-id"

    # Workspace with and without subscription id
    workspace_repo_mock.get_active_workspaces = AsyncMock(return_value=[
        Workspace(id='ws1', templateName='t1', resourceType=ResourceType.Workspace, templateVersion="1", _etag="x", properties={}),
        Workspace(id='ws2', templateName='t2', resourceType=ResourceType.Workspace, templateVersion="1", _etag="x", properties={"workspace_subscription_id": "sub-2"}),
        Workspace(id='ws3', templateName='t3', resourceType=ResourceType.Workspace, templateVersion="1", _etag="x", properties={"workspace_subscription_id": "sub-3"}),
        Workspace(id='ws4', templateName='t4', resourceType=ResourceType.Workspace, templateVersion="1", _etag="x", properties={"workspace_subscription_id": "sub-2"}),  # duplicate
    ])
    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    get_resource_groups_by_tag_mock.return_value = {}
    client_mock.return_value.query.usage.return_value = QueryResult(rows=[], columns=[])

    cost_service = CostService()
    await cost_service.query_tre_costs(
        "treid", GranularityEnum.none, datetime.now(), datetime.now(), workspace_repo_mock, shared_service_repo_mock)

    # Collect all subscription_ids used in get_resource_groups_by_tag calls
    called_sub_ids = set(call.args[2] for call in get_resource_groups_by_tag_mock.call_args_list)
    # Should include default and both unique workspace ids
    assert called_sub_ids == {"default-sub-id", "sub-2", "sub-3"}


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
@patch('services.cost_service.CostService.__wrapped__.get_resource_groups_by_tag')
async def test_subscription_id_skips_workspaces_without_id(get_resource_groups_by_tag_mock, client_mock, shared_service_repo_mock, workspace_repo_mock):
    from services import cost_service as cs
    cs.config.SUBSCRIPTION_ID = "default-sub-id"

    workspace_repo_mock.get_active_workspaces = AsyncMock(return_value=[
        Workspace(id='ws1', templateName='t1', resourceType=ResourceType.Workspace, templateVersion="1", _etag="x", properties={}),
        Workspace(id='ws2', templateName='t2', resourceType=ResourceType.Workspace, templateVersion="1", _etag="x", properties={}),
    ])
    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    get_resource_groups_by_tag_mock.return_value = {}
    client_mock.return_value.query.usage.return_value = QueryResult(rows=[], columns=[])

    cost_service = CostService()
    await cost_service.query_tre_costs(
        "treid", GranularityEnum.none, datetime.now(), datetime.now(), workspace_repo_mock, shared_service_repo_mock)

    called_sub_ids = set(call.args[2] for call in get_resource_groups_by_tag_mock.call_args_list)
    assert called_sub_ids == {"default-sub-id"}
