import pytest
from mock import patch

from models.domain.authentication import User, RoleAssignment
from models.domain.workspace import Workspace, WorkspaceRole
from services.aad_authentication import AzureADAuthorization
from services.access_service import AuthConfigValidationError


def test_extract_workspace__raises_error_if_client_id_not_available():
    access_service = AzureADAuthorization()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"auth_type": "Manual"})


@patch("services.aad_authentication.AzureADAuthorization._get_app_auth_info",
       return_value={"app_role_id_workspace_researcher": "1234"})
def test_extract_workspace__raises_error_if_owner_not_in_roles(get_app_auth_info_mock):
    access_service = AzureADAuthorization()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"client_id": "1234"})


@patch("services.aad_authentication.AzureADAuthorization._get_app_auth_info",
       return_value={"app_role_id_workspace_owner": "1234"})
def test_extract_workspace__raises_error_if_researcher_not_in_roles(get_app_auth_info_mock):
    access_service = AzureADAuthorization()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"client_id": "1234"})


@patch("services.aad_authentication.AzureADAuthorization._get_app_sp_graph_data", return_value={})
def test_extract_workspace__raises_error_if_graph_data_is_invalid(get_app_sp_graph_data_mock):
    access_service = AzureADAuthorization()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"client_id": "1234"})


@patch("services.aad_authentication.AzureADAuthorization._get_app_sp_graph_data")
def test_extract_workspace__returns_sp_id_and_roles(get_app_sp_graph_data_mock):
    get_app_sp_graph_data_mock.return_value = {
        'value': [
            {
                'id': '12345',
                'appRoles': [
                    {'id': '1abc3', 'value': 'WorkspaceResearcher'},
                    {'id': '1abc4', 'value': 'WorkspaceOwner'},
                    {'id': '1abc5', 'value': 'AirlockManager'},
                ],
                'servicePrincipalNames': [
                    "api://tre_ws_1234"
                ]
            }
        ]
    }
    expected_auth_info = {
        "sp_id": "12345",
        "scope_id": "api://tre_ws_1234",
        "app_role_id_workspace_owner": "1abc4",
        "app_role_id_workspace_researcher": "1abc3",
        "app_role_id_workspace_airlock_manager": "1abc5",
    }

    access_service = AzureADAuthorization()
    actual_auth_info = access_service.extract_workspace_auth_information(data={"auth_type": "Manual", "client_id": "1234"})

    assert actual_auth_info == expected_auth_info


@pytest.mark.parametrize('user, workspace, expected_role',
                         [
                             # user not a member of the workspace app
                             (User(roleAssignments=[RoleAssignment(resource_id="ab123", role_id="ab124")], id='123',
                                   name="test", email="t@t.com"),
                              Workspace(id='abc', etag="", templateName='template-name', templateVersion='0.1.0',
                                        resourcePath="test",
                                        properties={'client_id': '1234', 'sp_id': 'abc127',
                                                    'app_role_id_workspace_owner': 'abc128',
                                                    'app_role_id_workspace_researcher': 'abc129',
                                                    'app_role_id_workspace_airlock_manager': 'abc130'}),
                              WorkspaceRole.NoRole),
                             # user is member of the workspace app but not in role
                             (User(roleAssignments=[RoleAssignment(resource_id="ab127", role_id="ab124")], id='123',
                                   name="test", email="t@t.com"),
                              Workspace(id='abc', etag="", templateName='template-name', templateVersion='0.1.0',
                                        resourcePath="test",
                                        properties={'client_id': '1234', 'sp_id': 'abc127',
                                                    'app_role_id_workspace_owner': 'abc128',
                                                    'app_role_id_workspace_researcher': 'abc129',
                                                    'app_role_id_workspace_airlock_manager': 'abc130'}),
                              WorkspaceRole.NoRole),
                             # user has owner role in workspace
                             (User(roleAssignments=[RoleAssignment(resource_id="abc127", role_id="abc128")], id='123',
                                   name="test", email="t@t.com"),
                              Workspace(id='abc', etag="", templateName='template-name', templateVersion='0.1.0',
                                        resourcePath="test",
                                        properties={'client_id': '1234', 'sp_id': 'abc127',
                                                    'app_role_id_workspace_owner': 'abc128',
                                                    'app_role_id_workspace_researcher': 'abc129',
                                                    'app_role_id_workspace_airlock_manager': 'abc130'}),
                              WorkspaceRole.Owner),
                             # user has researcher role in workspace
                             (User(roleAssignments=[RoleAssignment(resource_id="abc127", role_id="abc129")], id='123',
                                   name="test", email="t@t.com"),
                              Workspace(id='abc', etag="", templateName='template-name', templateVersion='0.1.0',
                                        resourcePath="test",
                                        properties={'client_id': '1234', 'sp_id': 'abc127',
                                                    'app_role_id_workspace_owner': 'abc128',
                                                    'app_role_id_workspace_researcher': 'abc129',
                                                    'app_role_id_workspace_airlock_manager': 'abc130'}),
                              WorkspaceRole.Researcher),
                             # user has airlock manager role in workspace
                             (User(roleAssignments=[RoleAssignment(resource_id="abc127", role_id="abc130")], id='123',
                                   name="test", email="t@t.com"),
                              Workspace(id='abc', etag="", templateName='template-name', templateVersion='0.1.0',
                                        resourcePath="test",
                                        properties={'client_id': '1234', 'sp_id': 'abc127',
                                                    'app_role_id_workspace_owner': 'abc128',
                                                    'app_role_id_workspace_researcher': 'abc129',
                                                    'app_role_id_workspace_airlock_manager': 'abc130'}),
                              WorkspaceRole.AirlockManager)
                         ])
@patch("services.aad_authentication.AzureADAuthorization.get_identity_role_assignments")
def test_get_workspace_role_returns_correct_owner(get_identity_role_assignments_mock, user: User, workspace: Workspace,
                                                  expected_role: WorkspaceRole):
    get_identity_role_assignments_mock.return_value = user.roleAssignments

    access_service = AzureADAuthorization()
    actual_role = access_service.get_workspace_role(user, workspace,
                                                    access_service.get_identity_role_assignments(user.id))

    assert actual_role == expected_role


@patch("services.aad_authentication.AzureADAuthorization.get_identity_role_assignments",
       return_value=[("ab123", "ab124")])
def test_raises_auth_config_error_if_workspace_auth_config_is_not_set(_):
    access_service = AzureADAuthorization()

    user = User(id='123', name="test", email="t@t.com")
    workspace_with_no_auth_config = Workspace(id='abc', etag='', templateName='template-name', templateVersion='0.1.0',
                                              resourcePath="test")

    with pytest.raises(AuthConfigValidationError):
        _ = access_service.get_workspace_role(user, workspace_with_no_auth_config,
                                              access_service.get_identity_role_assignments(user.id))


@patch("services.aad_authentication.AzureADAuthorization.get_identity_role_assignments",
       return_value=[("ab123", "ab124")])
def test_raises_auth_config_error_if_auth_info_has_incorrect_roles(_):
    access_service = AzureADAuthorization()

    user = User(id='123', name="test", email="t@t.com")
    workspace_with_auth_info_but_no_roles = Workspace(
        id='abc',
        templateName='template-name',
        templateVersion='0.1.0',
        etag='',
        properties={'sp_id': '123', 'roles': {}},
        resourcePath="test")

    with pytest.raises(AuthConfigValidationError):
        _ = access_service.get_workspace_role(user, workspace_with_auth_info_but_no_roles,
                                              access_service.get_identity_role_assignments())


@patch("services.aad_authentication.AzureADAuthorization._get_user_role_assignments")
@patch("services.aad_authentication.AzureADAuthorization._get_user_emails")
@patch("services.aad_authentication.AzureADAuthorization._get_msgraph_token", return_value="token")
def test_get_workspace_role_assignment_details_with_single_user_returns_user_mail_and_role_assignment(_, users, roles):
    access_service = AzureADAuthorization()

    # Build user response
    user_principal_id = "user_principal_id"
    user_email = "test_user@email.com"
    user_response = get_batch_response([user_principal_id], [user_email])
    users.return_value = user_response

    # Build user role assignment response
    workspace_owner_role_id = "1234"
    roles_response = get_sample_role_response([user_principal_id], [workspace_owner_role_id], ["User"])
    roles.return_value = roles_response

    # Act
    role_assignment_details = access_service.get_workspace_role_assignment_details(Workspace(
        id="id",
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={'sp_id': 'ab123', 'app_role_id_workspace_owner': workspace_owner_role_id,
                    'app_role_id_workspace_researcher': 'ab125', 'app_role_id_workspace_airlock_manager': 'ab130'}
    ))

    assert role_assignment_details['WorkspaceOwner'] == [user_email]


@patch("services.aad_authentication.AzureADAuthorization._get_user_role_assignments")
@patch("services.aad_authentication.AzureADAuthorization._get_user_emails")
@patch("services.aad_authentication.AzureADAuthorization._get_msgraph_token", return_value="token")
def test_get_workspace_role_assignment_details_with_single_user_with_no_mail_is_not_returned(_, users, roles):
    access_service = AzureADAuthorization()

    # Build user response
    user_principal_id = "user_principal_id"
    user_response = get_batch_response([user_principal_id], [None])
    users.return_value = user_response

    # Build user role assignment response
    workspace_owner_role_id = "1234"
    roles_response = get_sample_role_response([user_principal_id], [workspace_owner_role_id], ["User"])
    roles.return_value = roles_response

    # Act
    role_assignment_details = access_service.get_workspace_role_assignment_details(Workspace(
        id="id",
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={'sp_id': 'ab123', 'app_role_id_workspace_owner': workspace_owner_role_id,
                    'app_role_id_workspace_researcher': 'ab125', 'app_role_id_workspace_airlock_manager': 'ab130'}
    ))

    assert len(role_assignment_details) == 0


@patch("services.aad_authentication.AzureADAuthorization._get_user_role_assignments")
@patch("services.aad_authentication.AzureADAuthorization._get_user_emails")
@patch("services.aad_authentication.AzureADAuthorization._get_msgraph_token", return_value="token")
def test_get_workspace_role_assignment_details_with_only_groups_assigned_are_not_returned(_, users_and_groups, roles):
    access_service = AzureADAuthorization()

    # Build group response
    group_principal_id = "group_principal_id"
    group_response = get_batch_response([group_principal_id], ["group@email.com"])
    users_and_groups.return_value = group_response

    # Build user role assignment response
    workspace_owner_role_id = "1234"
    roles_response = get_sample_role_response([group_principal_id], [workspace_owner_role_id], ["Group"])
    roles.return_value = roles_response

    # Act
    role_assignment_details = access_service.get_workspace_role_assignment_details(Workspace(
        id="id",
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={'sp_id': 'ab123', 'app_role_id_workspace_owner': workspace_owner_role_id,
                    'app_role_id_workspace_researcher': 'ab125', 'app_role_id_workspace_airlock_manager': 'ab130'}
    ))

    assert len(role_assignment_details) == 0


@patch("services.aad_authentication.AzureADAuthorization._get_user_role_assignments")
@patch("services.aad_authentication.AzureADAuthorization._get_user_emails")
@patch("services.aad_authentication.AzureADAuthorization._get_msgraph_token", return_value="token")
def test_get_workspace_role_assignment_details_with_groups_with_multiple_users_assigned_returned_as_expected(_, users_and_groups, roles):
    access_service = AzureADAuthorization()

    # Build group response
    group_principal_id = "group_principal_id"

    user_principal_id1 = "user_principal_id1"
    user_email1 = "test_user1@email.com"

    user_principal_id2 = "user_principal_id2"
    user_email2 = "test_user2@email.com"

    user_response = get_batch_response([user_principal_id1, user_principal_id2, group_principal_id], [user_email1, user_email2, "group@email.com"])
    users_and_groups.return_value = user_response

    # Build user role assignment response
    workspace_owner_role_id = "1234"
    roles_response = get_sample_role_response([group_principal_id, user_principal_id1, user_principal_id2],
                                              [workspace_owner_role_id],
                                              ["Group", "User", "User"])
    roles.return_value = roles_response

    # Act
    role_assignment_details = access_service.get_workspace_role_assignment_details(Workspace(
        id="id",
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={'sp_id': 'ab123', 'app_role_id_workspace_owner': workspace_owner_role_id,
                    'app_role_id_workspace_researcher': 'ab125', 'app_role_id_workspace_airlock_manager': 'ab130'}
    ))

    assert len(role_assignment_details) == 0


def get_batch_response(principal_ids, mails):
    response_body = {"responses": []}
    for principal_id, mail in zip(principal_ids, mails):
        response_body["responses"].append(get_sample_user_response(principal_id, mail))
    return response_body


def get_sample_user_response(principal_id, mail):
    headers = '{"Cache-Control":"no-cache","x-ms-resource-unit":"1","OData-Version":"4.0","Content-Type":"application/json;odata.metadata=minimal;odata.streaming=true;IEEE754Compatible=false;charset=utf-8"}'
    user_odata = '@odata.context":"https://graph.microsoft.com/v1.0/$metadata#users(mail,id)/$entity'
    user_response_body = {"id": "1",
                          "status": 200,
                          "headers": headers,
                          "body": {"@odata.context": user_odata, "mail": mail, "id": principal_id}}
    return user_response_body


def get_sample_group_response(principal_id, mail):
    headers = '{"Cache-Control":"no-cache","x-ms-resource-unit":"1","OData-Version":"4.0","Content-Type":"application/json;odata.metadata=minimal;odata.streaming=true;IEEE754Compatible=false;charset=utf-8"}'
    user_odata = '@odata.context":"https://graph.microsoft.com/v1.0/$metadata#users(mail,id)/$entity'
    group_response_body = {"id": "1",
                           "status": 200,
                           "headers": headers,
                           "body": {"@odata.context": user_odata, "mail": mail, "id": principal_id}}
    return group_response_body


def get_sample_role_response(principal_ids, role_ids, types):
    odata_context = '@odata.context":"https://graph.microsoft.com/v1.0/$metadata#servicePrincipals(workspace-client-id))/appRoleAssignedTo(appRoleId,principalId,principalType)'
    response = {"@odata.context": odata_context, "value": []}
    for principal_id, role_id, principal_type in zip(principal_ids, role_ids, types):
        response["value"].append({"appRoleId": role_id, "principalId": principal_id, "principalType": principal_type})
    return response
