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
def test_query_tre_costs_returns_correct_cost_report(client_mock, shared_service_repo_mock, workspace_repo_mock):
    query_result = QueryResult()
    query_result.rows = [
        [37.6, '"tre_core_service_id":"guy22"', 'USD'],
        [44.5, '"tre_id":"guy22"', 'USD'],
        [6.8, '"tre_shared_service_id":"848e8eb5-0df6-4d0f-9162-afd9a3fa0631"', 'USD'],
        [4.8, '"tre_shared_service_id":"f16d0324-9027-4448-b69b-2d48d925e6c0"', 'USD'],
        [1.8, '"tre_workspace_id":"19b7ce24-aa35-438c-adf6-37e6762911a6"', 'USD'],
        [2.8, '"tre_workspace_id":"d680d6b7-d1d9-411c-9101-0793da980c81"', 'USD'],
    ]

    client_mock.return_value.query.usage.return_value = query_result

    workspace_repo_mock.get_active_shared_services.return_value = [
        SharedService(id='848e8eb5-0df6-4d0f-9162-afd9a3fa0631', resourceType=ResourceType.WorkspaceService,  templateName="tre-workspace-base", templateVersion="1", _etag="x",
                      properties={'display_name': 'Shared service tre-shared-service-firewall'}),
        SharedService(id='f16d0324-9027-4448-b69b-2d48d925e6c0', resourceType=ResourceType.WorkspaceService,  templateName="tre-workspace-base", templateVersion="1", _etag="x",
                      properties={'display_name': 'Shared service tre-shared-service-gitea'})
    ]

    workspace_repo_mock.get_active_workspaces.return_value = [
        Workspace(id='bbc8ced6-a6d2-411f-ace3-58a14ad5f1c4', templateName='tre-workspace-base', resourceType=ResourceType.Workspace, templateVersion="1", _etag="x",
                  properties={'display_name': 'the workspace display name1'}),
        Workspace(id='d680d6b7-d1d9-411c-9101-0793da980c81', templateName='tre-workspace-base', resourceType=ResourceType.Workspace, templateVersion="1", _etag="x",
                  properties={'display_name': 'the workspace display name2'})
    ]

    cost_service = CostService()
    cost_report = cost_service.query_tre_costs(
        "guy22", GranularityEnum.none, date.today(), date.today(), workspace_repo_mock, shared_service_repo_mock)

    assert len(cost_report.core_services) == 1
    assert cost_report.core_services[0].cost == 37.6
    assert cost_report.core_services[0].date is None
    assert len(cost_report.shared_services) == 2
    assert cost_report.shared_services[0].id == "848e8eb5-0df6-4d0f-9162-afd9a3fa0631"
    assert cost_report.shared_services[0].name == "Shared service tre-shared-service-firewall"
    assert cost_report.shared_services[0].costs[0].cost == 6.8
    assert cost_report.shared_services[1].id == "f16d0324-9027-4448-b69b-2d48d925e6c0"
    assert cost_report.shared_services[1].name == "Shared service tre-shared-service-gitea"
    assert cost_report.shared_services[1].costs[0].cost == 4.8

