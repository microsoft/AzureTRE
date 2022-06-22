from mock import patch
from models.domain.costs import GranularityEnum
from models.domain.shared_service import SharedService, ResourceType
from models.domain.workspace import Workspace
from services.cost_service import CostService
from datetime import date
from azure.mgmt.costmanagement.models import QueryResult


@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
def test_query_tre_costs_with_granularity_none_returns_correct_cost_report(client_mock, shared_service_repo_mock,
                                                                           workspace_repo_mock):
    query_result = QueryResult()
    query_result.rows = [
        [37.6, '"tre_core_service_id":"guy22"', 'USD'],
        [44.5, '"tre_id":"guy22"', 'USD'],
        [6.8, '"tre_shared_service_id":"848e8eb5-0df6-4d0f-9162-afd9a3fa0631"', 'USD'],
        [4.8, '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'USD'],
        [1.8, '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"', 'USD'],
        [2.8, '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'USD'],
        [5.8, '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'ILS'],
    ]

    client_mock.return_value.query.usage.return_value = query_result

    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_return_value(workspace_repo_mock)

    cost_service = CostService()
    cost_report = cost_service.query_tre_costs(
        "guy22", GranularityEnum.none, date.today(), date.today(), workspace_repo_mock, shared_service_repo_mock)

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
    assert cost_report.workspaces[1].costs[0].cost == 2.8
    assert cost_report.workspaces[1].costs[0].currency == "USD"
    assert cost_report.workspaces[1].costs[1].cost == 5.8
    assert cost_report.workspaces[1].costs[1].currency == "ILS"



@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
def test_query_tre_costs_with_granularity_daily_returns_correct_cost_report(client_mock, shared_service_repo_mock,
                                                                            workspace_repo_mock):
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

    client_mock.return_value.query.usage.return_value = query_result

    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_return_value(workspace_repo_mock)

    cost_service = CostService()
    cost_report = cost_service.query_tre_costs(
        "guy22", GranularityEnum.daily, date.today(), date.today(), workspace_repo_mock, shared_service_repo_mock)

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
    assert len(cost_report.workspaces[1].costs) == 3
    assert cost_report.workspaces[1].costs[0].cost == 4.8
    assert cost_report.workspaces[1].costs[0].date == date(2022, 5, 1)
    assert cost_report.workspaces[1].costs[1].cost == 5.8
    assert cost_report.workspaces[1].costs[1].date == date(2022, 5, 2)
    assert cost_report.workspaces[1].costs[2].cost == 6.8
    assert cost_report.workspaces[1].costs[2].date == date(2022, 5, 3)


@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
def test_query_tre_costs_with_granularity_none_and_missing_costs_data_returns_empty_cost_report(client_mock,
                                                                                                shared_service_repo_mock,
                                                                                                workspace_repo_mock):
    query_result = QueryResult()
    query_result.rows = [
    ]

    client_mock.return_value.query.usage.return_value = query_result

    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_return_value(workspace_repo_mock)

    cost_service = CostService()
    cost_report = cost_service.query_tre_costs(
        "guy22", GranularityEnum.none, date.today(), date.today(), workspace_repo_mock, shared_service_repo_mock)

    assert len(cost_report.core_services) == 0
    assert len(cost_report.shared_services) == 2
    assert len(cost_report.shared_services[0].costs) == 0
    assert len(cost_report.shared_services[1].costs) == 0
    assert len(cost_report.workspaces) == 2
    assert len(cost_report.workspaces[0].costs) == 0
    assert len(cost_report.workspaces[1].costs) == 0


@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
def test_query_tre_costs_with_granularity_daily_and_missing_costs_data_returns_empty_cost_report(client_mock,
                                                                                                 shared_service_repo_mock,
                                                                                                 workspace_repo_mock):
    query_result = QueryResult()
    query_result.rows = [
    ]

    client_mock.return_value.query.usage.return_value = query_result

    __set_shared_service_repo_mock_return_value(shared_service_repo_mock)
    __set_workspace_repo_mock_return_value(workspace_repo_mock)

    cost_service = CostService()
    cost_report = cost_service.query_tre_costs(
        "guy22", GranularityEnum.daily, date.today(), date.today(), workspace_repo_mock, shared_service_repo_mock)

    assert len(cost_report.core_services) == 0
    assert len(cost_report.shared_services) == 2
    assert len(cost_report.shared_services[0].costs) == 0
    assert len(cost_report.shared_services[1].costs) == 0
    assert len(cost_report.workspaces) == 2
    assert len(cost_report.workspaces[0].costs) == 0
    assert len(cost_report.workspaces[1].costs) == 0


@patch('db.repositories.workspaces.WorkspaceRepository')
@patch('db.repositories.shared_services.SharedServiceRepository')
@patch('services.cost_service.CostManagementClient')
def test_query_tre_costs_with_granularity_none_and_display_name_data_returns_template_name_in_cost_report(client_mock,
                                                                                                          shared_service_repo_mock,
                                                                                                          workspace_repo_mock):
    query_result = QueryResult()
    query_result.rows = [
        [37.6, '"tre_core_service_id":"guy22"', 'USD'],
        [44.5, '"tre_id":"guy22"', 'USD'],
        [144.5, '"tre_id":"guy22"', 'ILS'],
        [6.8, '"tre_shared_service_id":"848e8eb5-0df6-4d0f-9162-afd9a3fa0631"', 'USD'],
        [4.8, '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'USD'],
        [14.8, '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'ILS'],
        [1.8, '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"', 'USD'],
        [2.8, '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'USD'],
        [62.8, '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'ILS'],
    ]

    client_mock.return_value.query.usage.return_value = query_result

    __set_shared_service_repo_mock_return_value_without_display_name(shared_service_repo_mock)
    __set_workspace_repo_mock_return_value_without_display_name(workspace_repo_mock)

    cost_service = CostService()
    cost_report = cost_service.query_tre_costs(
        "guy22", GranularityEnum.none, date.today(), date.today(), workspace_repo_mock, shared_service_repo_mock)

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
    assert len(cost_report.shared_services[1].costs) == 2
    assert cost_report.shared_services[1].costs[0].cost == 4.8
    assert cost_report.shared_services[1].costs[0].currency == "USD"
    assert cost_report.shared_services[1].costs[1].cost == 14.8
    assert cost_report.shared_services[1].costs[1].currency == "ILS"
    assert len(cost_report.workspaces) == 2
    assert cost_report.workspaces[0].id == "19b7ce24-aa35-438c-adf6-37e6762911a6"
    assert cost_report.workspaces[0].name == "tre-workspace-base"
    assert len(cost_report.workspaces[0].costs) == 1
    assert cost_report.workspaces[0].costs[0].cost == 1.8
    assert cost_report.workspaces[1].id == "d680d6b7-d1d9-411c-9101-0793da980c81"
    assert cost_report.workspaces[1].name == "tre-workspace-base"
    assert len(cost_report.workspaces[1].costs) == 2
    assert cost_report.workspaces[1].costs[0].cost == 2.8
    assert cost_report.workspaces[1].costs[0].currency == "USD"
    assert cost_report.workspaces[1].costs[1].cost == 62.8
    assert cost_report.workspaces[1].costs[1].currency == "ILS"



def __set_workspace_repo_mock_return_value(workspace_repo_mock):
    workspace_repo_mock.get_active_workspaces.return_value = [
        Workspace(id='19b7ce24-aa35-438c-adf6-37e6762911a6', templateName='tre-workspace-base',
                  resourceType=ResourceType.Workspace, templateVersion="1", _etag="x",
                  properties={'display_name': 'the workspace display name1'}),
        Workspace(id='d680d6b7-d1d9-411c-9101-0793da980c81', templateName='tre-workspace-base',
                  resourceType=ResourceType.Workspace, templateVersion="1", _etag="x",
                  properties={'display_name': 'the workspace display name2'})
    ]


def __set_workspace_repo_mock_return_value_without_display_name(workspace_repo_mock):
    workspace_repo_mock.get_active_workspaces.return_value = [
        Workspace(id='19b7ce24-aa35-438c-adf6-37e6762911a6', templateName='tre-workspace-base',
                  resourceType=ResourceType.Workspace, templateVersion="1", _etag="x"),
        Workspace(id='d680d6b7-d1d9-411c-9101-0793da980c81', templateName='tre-workspace-base',
                  resourceType=ResourceType.Workspace, templateVersion="1", _etag="x")
    ]


def __set_shared_service_repo_mock_return_value(shared_service_repo_mock):
    shared_service_repo_mock.get_active_shared_services.return_value = [
        SharedService(id='848e8eb5-0df6-4d0f-9162-afd9a3fa0631', resourceType=ResourceType.SharedService,
                      templateName="tre-shared-service-firewall", templateVersion="1", _etag="x",
                      properties={'display_name': 'Shared service tre-shared-service-firewall'}),
        SharedService(id='f16d0324-9027-4448-b69b-2d48d925e6c0', resourceType=ResourceType.SharedService,
                      templateName="tre-shared-service-gitea", templateVersion="1", _etag="x",
                      properties={'display_name': 'Shared service tre-shared-service-gitea'})
    ]


def __set_shared_service_repo_mock_return_value_without_display_name(shared_service_repo_mock):
    shared_service_repo_mock.get_active_shared_services.return_value = [
        SharedService(id='848e8eb5-0df6-4d0f-9162-afd9a3fa0631', resourceType=ResourceType.SharedService,
                      templateName="tre-shared-service-firewall", templateVersion="1", _etag="x"),
        SharedService(id='f16d0324-9027-4448-b69b-2d48d925e6c0', resourceType=ResourceType.SharedService,
                      templateName="tre-shared-service-gitea", templateVersion="1", _etag="x")
    ]
