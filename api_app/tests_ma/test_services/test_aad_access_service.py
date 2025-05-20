import pytest
from mock import call, patch

from models.domain.authentication import User, RoleAssignment
from models.domain.workspace_users import AssignmentType, Role
from models.domain.workspace import Workspace, WorkspaceRole
from services.aad_authentication import AzureADAuthorization, compare_versions
from services.access_service import AuthConfigValidationError, UserRoleAssignmentError

MOCK_MICROSOFT_GRAPH_URL = "https://graph.microsoft.com"


class PrincipalRole:
    def __init__(self, principal_id, role_id, principal_type):
        self.principal_id = principal_id
        self.role_id = role_id
        self.principal_type = principal_type


class UserPrincipal:
    def __init__(self, principal_id, userPrincipalName, name, mail):
        self.principal_id = principal_id
        self.mail = mail
        self.display_name = name
        self.userPrincipalName = userPrincipalName


class GroupPrincipal:
    def __init__(self, principal_id, members):
        self.principal_id = principal_id
        self.members = members


user_principal_1 = UserPrincipal("user_principal_id1", "test_user1@email.com", "test_user1", "test_user1@email.com")
user_principal_2 = UserPrincipal("user_principal_id2", "test_user2@email.com", "test_user2", "test_user2@email.com")
user_principal_3 = UserPrincipal("user_principal_id3", "test_user3@email.com", "test_user3", "test_user3@email.com")
user_principal_4 = UserPrincipal("user_principal_id4", "test_user4@email.com", "test_user4", "test_user4@email.com")

group_principal = GroupPrincipal("group_principal_id", [user_principal_3, user_principal_4])


@pytest.fixture
def roles_response():
    workspace_owner_role_id = "1abc4"
    return get_mock_role_response(
        [
            PrincipalRole(user_principal_1.principal_id, workspace_owner_role_id, "User"),
            PrincipalRole(group_principal.principal_id, workspace_owner_role_id, "Group")
        ]
    )


@pytest.fixture
def user_response():
    return get_mock_batch_response(
        [user_principal_1], []
    )


@pytest.fixture
def group_response():
    return get_mock_batch_response(
        [], [group_principal]
    )


@pytest.fixture
def users_and_group_response():
    return get_mock_batch_response(
        [user_principal_1, user_principal_2], [group_principal]
    )


@pytest.fixture
def get_app_sp_graph_data_mock():
    return {
        "value": [
            {
                "id": "12345",
                "appRoles": [
                    {"id": "1abc3", "value": "WorkspaceResearcher", "displayName": "Workspace Researcher"},
                    {"id": "1abc4", "value": "WorkspaceOwner", "displayName": "Workspace Owner"},
                    {"id": "1abc5", "value": "AirlockManager", "displayName": "Airlock Manager"},
                ],
                "servicePrincipalNames": ["api://tre_ws_1234"],
            }
        ]
    }


@pytest.fixture
def workspace_with_groups():
    return Workspace(
        id="ws1",
        etag="",
        templateName="test-template",
        templateVersion="2.2.0",
        resourcePath="",
        properties={
            "create_aad_groups": True,
            "tre_id": "TRE-001",
            "workspace_id": "ws1",
            "client_id": "app-client-id",
            "sp_id": "sp123",
            "app_role_id_workspace_owner": "owner-role-id",
            "app_role_id_workspace_researcher": "researcher-role-id",
            "app_role_id_workspace_airlock_manager": "airlock-role-id",
        }
    )


@pytest.fixture
def workspace_without_groups():
    return Workspace(
        id="ws2",
        etag="",
        templateName="test-template",
        templateVersion="2.2.0",
        resourcePath="",
        properties={
            "create_aad_groups": False,
            "tre_id": "TRE-002",
            "workspace_id": "ws2",
            "client_id": "app-client-id",
            "sp_id": "sp456",
            "app_role_id_workspace_owner": "owner-role-id",
            "app_role_id_workspace_researcher": "researcher-role-id",
            "app_role_id_workspace_airlock_manager": "airlock-role-id",
        }
    )


@pytest.fixture
def role_owner():
    return Role(id="owner-role-id", displayName="Workspace Owner", type=AssignmentType.APP_ROLE)


@pytest.fixture
def user_without_role():
    return User(id="user1", name="Test User", email="test@example.com", roles=[])


@pytest.fixture
def user_with_role():
    return User(id="user2", name="Test User 2", email="test2@example.com", roles=["WorkspaceOwner"])


def test_extract_workspace__raises_error_if_client_id_not_available():
    access_service = AzureADAuthorization()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"auth_type": "Manual"})


@patch("services.aad_authentication.AzureADAuthorization._get_app_sp_graph_data")
@patch("services.aad_authentication.AzureADAuthorization._get_user_role_assignments")
@patch("services.aad_authentication.AzureADAuthorization._get_user_details")
@patch(
    "services.aad_authentication.AzureADAuthorization._get_msgraph_token",
    return_value="token",
)
def test_get_workspace_user_emails_by_role_assignment_with_single_user_returns_user_mail_and_role_assignment(
    _, users, roles, app_sp_graph_data_mock, user_response, roles_response, get_app_sp_graph_data_mock
):
    access_service = AzureADAuthorization()

    # Use fixtures
    users.return_value = user_response
    roles.return_value = roles_response
    app_sp_graph_data_mock.return_value = get_app_sp_graph_data_mock

    # Act
    role_assignment_details = access_service.get_workspace_user_emails_by_role_assignment(
        Workspace(
            id="id",
            templateName="tre-workspace-base",
            templateVersion="0.1.0",
            etag="",
            properties={
                "sp_id": "ab123",
                "client_id": "ab124",
                "app_role_id_workspace_owner": "1abc4",
                "app_role_id_workspace_researcher": "ab125",
                "app_role_id_workspace_airlock_manager": "ab130",
            },
        )
    )

    assert role_assignment_details["WorkspaceOwner"] == ["test_user1@email.com"]


@patch("services.aad_authentication.AzureADAuthorization._get_app_sp_graph_data")
@patch("services.aad_authentication.AzureADAuthorization._get_user_role_assignments")
@patch("services.aad_authentication.AzureADAuthorization._get_user_details")
@patch(
    "services.aad_authentication.AzureADAuthorization._get_msgraph_token",
    return_value="token",
)
def test_get_workspace_user_emails_by_role_assignment_with_single_user_with_no_mail_is_not_returned(
    _, users, roles, app_sp_graph_data_mock, user_response, roles_response, get_app_sp_graph_data_mock
):
    access_service = AzureADAuthorization()

    # Build user response
    user_response_no_mail = user_response.copy()
    user_response_no_mail["responses"][0]["body"]["mail"] = None
    users.return_value = user_response_no_mail

    roles.return_value = roles_response
    app_sp_graph_data_mock.return_value = get_app_sp_graph_data_mock

    # Act
    role_assignment_details = access_service.get_workspace_user_emails_by_role_assignment(
        Workspace(
            id="id",
            templateName="tre-workspace-base",
            templateVersion="0.1.0",
            etag="",
            properties={
                "sp_id": "ab123",
                "client_id": "ab124",
                "app_role_id_workspace_owner": "1abc4",
                "app_role_id_workspace_researcher": "ab125",
                "app_role_id_workspace_airlock_manager": "ab130",
            },
        )
    )

    assert len(role_assignment_details) == 0


@patch("services.aad_authentication.AzureADAuthorization._get_app_sp_graph_data")
@patch("services.aad_authentication.AzureADAuthorization._get_user_role_assignments")
@patch("services.aad_authentication.AzureADAuthorization._get_user_details")
@patch(
    "services.aad_authentication.AzureADAuthorization._get_msgraph_token",
    return_value="token",
)
def test_get_workspace_user_emails_by_role_assignment_with_only_groups_assigned_returns_group_members(
    _, users_and_groups, roles, app_sp_graph_data_mock, group_response, roles_response, get_app_sp_graph_data_mock
):
    access_service = AzureADAuthorization()

    users_and_groups.return_value = group_response
    roles.return_value = roles_response
    app_sp_graph_data_mock.return_value = get_app_sp_graph_data_mock

    # Act
    role_assignment_details = access_service.get_workspace_user_emails_by_role_assignment(
        Workspace(
            id="id",
            templateName="tre-workspace-base",
            templateVersion="0.1.0",
            etag="",
            properties={
                "sp_id": "ab123",
                "client_id": "ab124",
                "app_role_id_workspace_owner": "1abc4",
                "app_role_id_workspace_researcher": "ab125",
                "app_role_id_workspace_airlock_manager": "ab130",
            },
        )
    )

    assert len(role_assignment_details) == 1
    assert "test_user3@email.com" in role_assignment_details["WorkspaceOwner"]
    assert "test_user4@email.com" in role_assignment_details["WorkspaceOwner"]


@patch("services.aad_authentication.AzureADAuthorization._get_app_sp_graph_data")
@patch("services.aad_authentication.AzureADAuthorization._get_user_role_assignments")
@patch("services.aad_authentication.AzureADAuthorization._get_user_details")
@patch(
    "services.aad_authentication.AzureADAuthorization._get_msgraph_token",
    return_value="token",
)
def test_get_workspace_user_emails_by_role_assignment_with_groups_and_users_assigned_returned_as_expected(
    _, users_and_groups, roles, app_sp_graph_data_mock, roles_response, get_app_sp_graph_data_mock, users_and_group_response
):

    access_service = AzureADAuthorization()

    roles.return_value = roles_response
    app_sp_graph_data_mock.return_value = get_app_sp_graph_data_mock
    users_and_groups.return_value = users_and_group_response

    # Act
    role_assignment_details = access_service.get_workspace_user_emails_by_role_assignment(
        Workspace(
            id="id",
            templateName="tre-workspace-base",
            templateVersion="0.1.0",
            etag="",
            properties={
                "sp_id": "ab123",
                "client_id": "ab123",
                "app_role_id_workspace_owner": "ab124",
                "app_role_id_workspace_researcher": "ab125",
                "app_role_id_workspace_airlock_manager": "ab130",
            },
        )
    )

    assert len(role_assignment_details) == 1
    assert "test_user1@email.com" in role_assignment_details["WorkspaceOwner"]
    assert "test_user3@email.com" in role_assignment_details["WorkspaceOwner"]
    assert "test_user4@email.com" in role_assignment_details["WorkspaceOwner"]


@patch(
    "services.aad_authentication.AzureADAuthorization._get_app_auth_info",
    return_value={"app_role_id_workspace_researcher": "1234"},
)
def test_extract_workspace__raises_error_if_owner_not_in_roles(get_app_auth_info_mock):
    access_service = AzureADAuthorization()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"client_id": "1234"})


@patch(
    "services.aad_authentication.AzureADAuthorization._get_app_auth_info",
    return_value={"app_role_id_workspace_owner": "1234"},
)
def test_extract_workspace__raises_error_if_researcher_not_in_roles(
    get_app_auth_info_mock,
):
    access_service = AzureADAuthorization()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"client_id": "1234"})


@patch(
    "services.aad_authentication.AzureADAuthorization._get_app_sp_graph_data",
    return_value={},
)
def test_extract_workspace__raises_error_if_graph_data_is_invalid(
    get_app_sp_graph_data_mock,
):
    access_service = AzureADAuthorization()
    with pytest.raises(AuthConfigValidationError):
        access_service.extract_workspace_auth_information(data={"client_id": "1234"})


@patch("services.aad_authentication.AzureADAuthorization._get_app_sp_graph_data")
def test_extract_workspace__returns_sp_id_and_roles(get_app_sp_graph_data_mock):
    get_app_sp_graph_data_mock.return_value = {
        "value": [
            {
                "id": "12345",
                "appRoles": [
                    {"id": "1abc3", "value": "WorkspaceResearcher"},
                    {"id": "1abc4", "value": "WorkspaceOwner"},
                    {"id": "1abc5", "value": "AirlockManager"},
                ],
                "servicePrincipalNames": ["api://tre_ws_1234"],
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
    actual_auth_info = access_service.extract_workspace_auth_information(
        data={"auth_type": "Manual", "client_id": "1234"}
    )

    assert actual_auth_info == expected_auth_info


@pytest.mark.parametrize(
    "user, workspace, expected_role",
    [
        # user not a member of the workspace app
        (
            User(
                roleAssignments=[RoleAssignment(resource_id="ab123", role_id="ab124")],
                id="123",
                name="test",
                email="t@t.com",
            ),
            Workspace(
                id="abc",
                etag="",
                templateName="template-name",
                templateVersion="0.1.0",
                resourcePath="test",
                properties={
                    "client_id": "1234",
                    "sp_id": "abc127",
                    "app_role_id_workspace_owner": "abc128",
                    "app_role_id_workspace_researcher": "abc129",
                    "app_role_id_workspace_airlock_manager": "abc130",
                },
            ),
            WorkspaceRole.NoRole,
        ),
        # user is member of the workspace app but not in role
        (
            User(
                roleAssignments=[RoleAssignment(resource_id="ab127", role_id="ab124")],
                id="123",
                name="test",
                email="t@t.com",
            ),
            Workspace(
                id="abc",
                etag="",
                templateName="template-name",
                templateVersion="0.1.0",
                resourcePath="test",
                properties={
                    "client_id": "1234",
                    "sp_id": "abc127",
                    "app_role_id_workspace_owner": "abc128",
                    "app_role_id_workspace_researcher": "abc129",
                    "app_role_id_workspace_airlock_manager": "abc130",
                },
            ),
            WorkspaceRole.NoRole,
        ),
        # user has owner role in workspace
        (
            User(
                roleAssignments=[
                    RoleAssignment(resource_id="abc127", role_id="abc128")
                ],
                id="123",
                name="test",
                email="t@t.com",
            ),
            Workspace(
                id="abc",
                etag="",
                templateName="template-name",
                templateVersion="0.1.0",
                resourcePath="test",
                properties={
                    "client_id": "1234",
                    "sp_id": "abc127",
                    "app_role_id_workspace_owner": "abc128",
                    "app_role_id_workspace_researcher": "abc129",
                    "app_role_id_workspace_airlock_manager": "abc130",
                },
            ),
            WorkspaceRole.Owner,
        ),
        # user has researcher role in workspace
        (
            User(
                roleAssignments=[
                    RoleAssignment(resource_id="abc127", role_id="abc129")
                ],
                id="123",
                name="test",
                email="t@t.com",
            ),
            Workspace(
                id="abc",
                etag="",
                templateName="template-name",
                templateVersion="0.1.0",
                resourcePath="test",
                properties={
                    "client_id": "1234",
                    "sp_id": "abc127",
                    "app_role_id_workspace_owner": "abc128",
                    "app_role_id_workspace_researcher": "abc129",
                    "app_role_id_workspace_airlock_manager": "abc130",
                },
            ),
            WorkspaceRole.Researcher,
        ),
        # user has airlock manager role in workspace
        (
            User(
                roleAssignments=[
                    RoleAssignment(resource_id="abc127", role_id="abc130")
                ],
                id="123",
                name="test",
                email="t@t.com",
            ),
            Workspace(
                id="abc",
                etag="",
                templateName="template-name",
                templateVersion="0.1.0",
                resourcePath="test",
                properties={
                    "client_id": "1234",
                    "sp_id": "abc127",
                    "app_role_id_workspace_owner": "abc128",
                    "app_role_id_workspace_researcher": "abc129",
                    "app_role_id_workspace_airlock_manager": "abc130",
                },
            ),
            WorkspaceRole.AirlockManager,
        ),
    ],
)
@patch("services.aad_authentication.AzureADAuthorization.get_identity_role_assignments")
def test_get_workspace_role_returns_correct_owner(
    get_identity_role_assignments_mock,
    user: User,
    workspace: Workspace,
    expected_role: WorkspaceRole,
):
    get_identity_role_assignments_mock.return_value = user.roleAssignments

    access_service = AzureADAuthorization()
    actual_role = access_service.get_workspace_role(
        user, workspace, access_service.get_identity_role_assignments(user.id)
    )

    assert actual_role == expected_role


@patch(
    "services.aad_authentication.AzureADAuthorization.get_identity_role_assignments",
    return_value=[("ab123", "ab124")],
)
def test_raises_auth_config_error_if_workspace_auth_config_is_not_set(_):
    access_service = AzureADAuthorization()

    user = User(id="123", name="test", email="t@t.com")
    workspace_with_no_auth_config = Workspace(
        id="abc",
        etag="",
        templateName="template-name",
        templateVersion="0.1.0",
        resourcePath="test",
    )

    with pytest.raises(AuthConfigValidationError):
        _ = access_service.get_workspace_role(
            user,
            workspace_with_no_auth_config,
            access_service.get_identity_role_assignments(user.id),
        )


@patch(
    "services.aad_authentication.AzureADAuthorization.get_identity_role_assignments",
    return_value=[("ab123", "ab124")],
)
def test_raises_auth_config_error_if_auth_info_has_incorrect_roles(_):
    access_service = AzureADAuthorization()

    user = User(id="123", name="test", email="t@t.com")
    workspace_with_auth_info_but_no_roles = Workspace(
        id="abc",
        templateName="template-name",
        templateVersion="0.1.0",
        etag="",
        properties={"sp_id": "123", "roles": {}},
        resourcePath="test",
    )

    with pytest.raises(AuthConfigValidationError):
        _ = access_service.get_workspace_role(
            user,
            workspace_with_auth_info_but_no_roles,
            access_service.get_identity_role_assignments(),
        )


@patch("services.aad_authentication.AzureADAuthorization._get_auth_header")
@patch("services.aad_authentication.AzureADAuthorization._get_batch_users_by_role_assignments_body")
@patch("requests.post")
def test_get_user_details_with_batch_of_more_than_20_requests(mock_graph_post, mock_get_batch_users_by_role_assignments_body, mock_headers):
    # Arrange
    access_service = AzureADAuthorization()
    roles_graph_data = [{"id": "role1"}, {"id": "role2"}]
    msgraph_token = "token"
    batch_endpoint = access_service._get_batch_endpoint()

    # mock the response of _get_auth_header
    headers = {"Authorization": f"Bearer {msgraph_token}"}
    mock_headers.return_value = headers
    headers["Content-type"] = "application/json"

    # mock the response of the get batch request for 30 users
    batch_request_body_first_20 = {
        "requests": [
            {"id": f"{i}", "method": "GET", "url": f"/users/{i}"} for i in range(20)
        ]
    }

    batch_request_body_last_10 = {
        "requests": [
            {"id": f"{i}", "method": "GET", "url": f"/users/{i}"} for i in range(20, 30)
        ]
    }

    batch_request_body = {
        "requests": [
            {"id": f"{i}", "method": "GET", "url": f"/users/{i}"} for i in range(30)
        ]
    }

    mock_get_batch_users_by_role_assignments_body.return_value = batch_request_body

    # Mock the response of the post request
    mock_graph_post_response = {"responses": [{"id": "user1", "request": {"id": "user1"}}, {"id": "user2", "request": {"id": "user2"}}]}
    mock_graph_post.return_value.json.return_value = mock_graph_post_response

    # Act
    users_graph_data = access_service._get_user_details(roles_graph_data, msgraph_token)

    # Assert
    assert len(users_graph_data["responses"]) == 4
    calls = [
        call(
            f"{batch_endpoint}",
            json=batch_request_body_first_20,
            headers=headers
        ),
        call(
            f"{batch_endpoint}",
            json=batch_request_body_last_10,
            headers=headers
        )
    ]
    mock_graph_post.assert_has_calls(calls, any_order=True)


@patch("services.aad_authentication.AzureADAuthorization._get_role_assignment_graph_data_for_user")
def test_get_role_assignment_for_user(mock_get_role_assignment_data_for_user):
    mock_user_data = {
        "value": [
            {"appRoleId": "123", "principalId": "123", "principalType": "User"},
            {"appRoleId": "456", "principalId": "456", "principalType": "User"},
        ]
    }

    mock_get_role_assignment_data_for_user.return_value = mock_user_data
    access_service = AzureADAuthorization()
    role = access_service._get_role_assignment_for_user("abc", "123")

    mock_get_role_assignment_data_for_user.assert_called_once()
    assert role == mock_user_data["value"][0]


def get_mock_batch_response(user_principals, group_principals):
    response_body = {"responses": []}
    for user_principal in user_principals:
        response_body["responses"].append(
            get_mock_user_response(user_principal.principal_id, user_principal.userPrincipalName, user_principal.display_name, user_principal.mail)
        )
    for group_principal in group_principals:
        response_body["responses"].append(get_mock_group_response(group_principal))
    return response_body


def get_mock_user_response(principal_id, mail, name, userPrincipalName):
    headers = '{"Cache-Control":"no-cache","x-ms-resource-unit":"1","OData-Version":"4.0","Content-Type":"application/json;odata.metadata=minimal;odata.streaming=true;IEEE754Compatible=false;charset=utf-8"}'
    user_odata = f'@odata.context":"{MOCK_MICROSOFT_GRAPH_URL}/v1.0/$metadata#users(mail,id)/$entity'
    user_response_body = {
        "id": "1",
        "status": 200,
        "headers": headers,
        "body": {"@odata.context": user_odata, "userPrincipalName": userPrincipalName, "id": principal_id, "displayName": name, "mail": mail},
    }
    return user_response_body


def get_mock_group_response(group):
    headers = '{"Cache-Control":"no-cache","x-ms-resource-unit":"1","OData-Version":"4.0","Content-Type":"application/json;odata.metadata=minimal;odata.streaming=true;IEEE754Compatible=false;charset=utf-8"}'
    group_odata = f"{MOCK_MICROSOFT_GRAPH_URL}/v1.0/$metadata#directoryObjects(mail,id)"
    group_members_body = []
    for member in group.members:
        group_members_body.append(
            {
                "@odata.type": "#microsoft.graph.user",
                "userPrincipalName": member.mail,
                "id": member.principal_id,
                "displayName": member.display_name,
                "mail": member.mail,
            }
        )
    group_response_body = {
        "id": group.principal_id,
        "status": 200,
        "headers": headers,
        "body": {"@odata.context": group_odata, "value": group_members_body},
        "request": {"id": "group_principal_id"}
    }
    return group_response_body


def get_mock_role_response(principal_roles):
    odata_context = f'@odata.context":"{MOCK_MICROSOFT_GRAPH_URL}/v1.0/$metadata#servicePrincipals(workspace-client-id))/appRoleAssignedTo(appRoleId,principalId,principalType)'
    response = {"@odata.context": odata_context, "value": []}
    for principal_role in principal_roles:
        response["value"].append(
            {
                "appRoleId": principal_role.role_id,
                "principalId": principal_role.principal_id,
                "principalType": principal_role.principal_type,
            }
        )
    return response


@patch("services.aad_authentication.AzureADAuthorization._is_user_in_role", return_value=True)
@patch("services.aad_authentication.AzureADAuthorization._is_workspace_role_group_in_use")
@patch("services.aad_authentication.AzureADAuthorization._assign_workspace_user_to_application_group")
def test_assign_workspace_user_already_has_role(workspace_role_in_use_mock,
                                                assign_user_to_group_mock,
                                                workspace_without_groups, role_owner,
                                                user_with_role):
    access_service = AzureADAuthorization()
    access_service.assign_workspace_user(user_with_role.id, workspace_without_groups, role_owner.id)

    assert workspace_role_in_use_mock.call_count == 0
    assert assign_user_to_group_mock.call_count == 0


@patch("services.aad_authentication.AzureADAuthorization._is_user_in_role", return_value=False)
@patch("services.aad_authentication.AzureADAuthorization._is_workspace_role_group_in_use", return_value=False)
@patch("services.aad_authentication.AzureADAuthorization._assign_workspace_user_to_application_group")
def test_assign_workspace_user_if_no_groups_raises_error(_, __, ___, workspace_without_groups, role_owner,
                                                         user_with_role):

    access_service = AzureADAuthorization()

    with pytest.raises(UserRoleAssignmentError):
        access_service.assign_workspace_user(user_with_role.id, workspace_without_groups, role_owner.id)


@patch("services.aad_authentication.AzureADAuthorization._is_user_in_role", return_value=False)
@patch("services.aad_authentication.AzureADAuthorization._is_workspace_role_group_in_use", return_value=True)
@patch("services.aad_authentication.AzureADAuthorization._assign_workspace_user_to_application_group")
def test_assign_workspace_user_if_groups(_, __, assign_user_to_group_mock,
                                         workspace_without_groups, role_owner,
                                         user_with_role):

    access_service = AzureADAuthorization()

    access_service.assign_workspace_user(user_with_role.id, workspace_without_groups, role_owner.id)

    assert assign_user_to_group_mock.call_count == 1


@patch("services.aad_authentication.AzureADAuthorization._is_workspace_role_group_in_use", return_value=False)
@patch("services.aad_authentication.AzureADAuthorization._get_role_assignment_for_user")
def test_remove_workspace_user_if_no_groups_raises_error(_, get_role_assignment_mock,
                                                         workspace_without_groups,
                                                         role_owner,
                                                         user_with_role):

    access_service = AzureADAuthorization()
    get_role_assignment_mock.return_value = []

    with pytest.raises(UserRoleAssignmentError):
        access_service.remove_workspace_role_user_assignment(user_with_role.id, role_owner.id, workspace_without_groups)


@patch("services.aad_authentication.AzureADAuthorization._remove_workspace_user_from_application_group")
@patch("services.aad_authentication.AzureADAuthorization._get_role_assignment_for_user")
@patch("services.aad_authentication.AzureADAuthorization._is_workspace_role_group_in_use", return_value=True)
def test_remove_workspace_user_if_groups(_, get_role_assignment_mock,
                                         remove_user_to_group_mock,
                                         workspace_without_groups,
                                         role_owner,
                                         user_with_role):

    access_service = AzureADAuthorization()
    get_role_assignment_mock.return_value = []

    access_service.remove_workspace_role_user_assignment(user_with_role.id, role_owner.id, workspace_without_groups)

    assert remove_user_to_group_mock.call_count == 1


@patch("services.aad_authentication.AzureADAuthorization._ms_graph_query")
def test_get_assignable_users_returns_users(ms_graph_query_mock):
    access_service = AzureADAuthorization()

    # Mock the response of the get request
    request_get_mock_response = {
        "value": [
            {
                "id": "123",
                "displayName": "User 1",
                "userPrincipalName": "User1@test.com",
                "mail": "User1@test.com"
            }
        ]
    }
    ms_graph_query_mock.return_value = request_get_mock_response
    users = access_service.get_assignable_users()

    assert len(users) == 1
    assert users[0].displayName == "User 1"
    assert users[0].userPrincipalName == "User1@test.com"


@patch("services.aad_authentication.AzureADAuthorization._get_msgraph_token", return_value="token")
@patch("services.aad_authentication.AzureADAuthorization._ms_graph_query")
@patch("services.aad_authentication.AzureADAuthorization._get_auth_header")
def test_get_workspace_roles_returns_roles(_, ms_graph_query_mock, mock_headers, workspace_without_groups):
    access_service = AzureADAuthorization()

    # mock the response of _get_auth_header
    headers = {"Authorization": "Bearer token"}
    mock_headers.return_value = headers
    headers["Content-type"] = "application/json"

    # Mock the response of the get request
    request_get_mock_response = {
        "value": [
            Role(id=1, displayName="Airlock Manager", type=AssignmentType.APP_ROLE).dict(),
            Role(id=2, displayName="Workspace Researcher", type=AssignmentType.APP_ROLE).dict(),
            Role(id=3, displayName="Workspace Owner", type=AssignmentType.APP_ROLE).dict(),
        ]
    }
    ms_graph_query_mock.return_value = request_get_mock_response
    roles = access_service.get_workspace_roles(workspace_without_groups)

    assert len(roles) == 3
    assert roles[0].id == "1"
    assert roles[0].displayName == "Airlock Manager"


def test_compare_versions_equal():
    result = compare_versions("1.0.0", "1.0.0")
    assert result == 0


def test_compare_versions_greater_than():
    result = compare_versions("1.1.0", "1.0.0")
    assert result > 0


def test_compare_versions_less_than():
    result = compare_versions("1.0.0", "1.1.0")
    assert result < 0
