import pytest
from mock import patch

from models.domain.workspace import Workspace, WorkspaceRole
from services.aad_access_service import AADAccessService
from services.access_service import AuthConfigValidationError
from services.authentication import User


def test_extract_workspace__raises_error_if_app_id_not_available():
    access_service = AADAccessService()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={})


@patch("services.aad_access_service.AADAccessService._get_app_auth_info", return_value={"roles": {"WorkspaceResearcher": "1234"}})
def test_extract_workspace__raises_error_if_owner_not_in_roles(get_app_auth_info_mock):
    access_service = AADAccessService()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"app_id": "1234"})


@patch("services.aad_access_service.AADAccessService._get_app_auth_info", return_value={"roles": {"WorkspaceOwner": "1234"}})
def test_extract_workspace__raises_error_if_researcher_not_in_roles(get_app_auth_info_mock):
    access_service = AADAccessService()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"app_id": "1234"})


@patch("services.aad_access_service.AADAccessService._get_app_sp_graph_data", return_value={})
def test_extract_workspace__raises_error_if_graph_data_is_invalid(get_app_sp_graph_data_mock):
    access_service = AADAccessService()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"app_id": "1234"})


@patch("services.aad_access_service.AADAccessService._get_app_sp_graph_data")
def test_extract_workspace__returns_sp_id_and_roles(get_app_sp_graph_data_mock):
    get_app_sp_graph_data_mock.return_value = {
        'value': [
            {
                'id': '12345',
                'appRoles': [
                    {'id': '1abc3', 'value': 'WorkspaceResearcher'},
                    {'id': '1abc4', 'value': 'WorkspaceOwner'},
                ]
            }
        ]
    }
    expected_auth_info = {
        'sp_id': '12345',
        'roles': {'WorkspaceResearcher': '1abc3', 'WorkspaceOwner': '1abc4'}
    }

    access_service = AADAccessService()
    actual_auth_info = access_service.extract_workspace_auth_information(data={"app_id": "1234"})

    assert actual_auth_info == expected_auth_info


@pytest.mark.parametrize('user, workspace, expected_role',
                         [
                             # user not a member of the workspace app
                             (User(roleAssignments={'abc123': 'abc124'}, id='123', name="test", email="t@t.com"),
                              Workspace(authInformation={'sp_id': 'abc127', 'roles': {'WorkspaceOwner': 'abc128', 'WorkspaceResearcher': 'abc129'}},
                                        id='abc', resourceTemplateName='template-name', resourceTemplateVersion='0.1.0'),
                              WorkspaceRole.NoRole),
                             # user is member of the workspace app but not in role
                             (User(roleAssignments={'abc127': 'abc124'}, id='123', name="test", email="t@t.com"),
                              Workspace(authInformation={'sp_id': 'abc127', 'roles': {'WorkspaceOwner': 'abc128', 'WorkspaceResearcher': 'abc129'}},
                                        id='abc', resourceTemplateName='template-name', resourceTemplateVersion='0.1.0'),
                              WorkspaceRole.NoRole),
                             # user has owner role in workspace
                             (User(roleAssignments={'abc127': 'abc128'}, id='123', name="test", email="t@t.com"),
                              Workspace(authInformation={'sp_id': 'abc127', 'roles': {'WorkspaceOwner': 'abc128', 'WorkspaceResearcher': 'abc129'}},
                                        id='abc', resourceTemplateName='template-name', resourceTemplateVersion='0.1.0'),
                              WorkspaceRole.Owner),
                             # user has researcher role in workspace
                             (User(roleAssignments={'abc127': 'abc129'}, id='123', name="test", email="t@t.com"),
                              Workspace(authInformation={'sp_id': 'abc127', 'roles': {'WorkspaceOwner': 'abc128', 'WorkspaceResearcher': 'abc129'}},
                                        id='abc', resourceTemplateName='template-name', resourceTemplateVersion='0.1.0'),
                              WorkspaceRole.Researcher)
                         ])
def test_get_workspace_role_returns_correct_owner(user: User, workspace: Workspace, expected_role: WorkspaceRole):
    access_service = AADAccessService()

    actual_role = access_service.get_workspace_role(user, workspace)

    assert actual_role == expected_role


def test_raises_auth_config_error_if_workspace_auth_config_is_not_set():
    access_service = AADAccessService()

    user = User(id='123', name="test", email="t@t.com", roleAssignments={'abc123': 'abc124'})
    workspace_with_no_auth_config = Workspace(id='abc', resourceTemplateName='template-name', resourceTemplateVersion='0.1.0')

    with pytest.raises(AuthConfigValidationError):
        _ = access_service.get_workspace_role(user, workspace_with_no_auth_config)


def test_raises_auth_config_error_if_auth_info_has_incorrect_roles():
    access_service = AADAccessService()

    user = User(id='123', name="test", email="t@t.com", roleAssignments={'abc123': 'abc124'})
    workspace_with_auth_info_but_no_roles = Workspace(
        id='abc',
        resourceTemplateName='template-name',
        resourceTemplateVersion='0.1.0',
        authInformation={'sp_id': '123', 'roles': {}})

    with pytest.raises(AuthConfigValidationError):
        _ = access_service.get_workspace_role(user, workspace_with_auth_info_but_no_roles)
