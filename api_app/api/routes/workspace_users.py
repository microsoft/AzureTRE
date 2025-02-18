from fastapi import APIRouter, Depends, Response, status
from api.dependencies.workspaces import get_workspace_by_id_from_path
from resources import strings
from services.authentication import get_access_service
from models.schemas.users import UsersInResponse, AssignableUsersInResponse
from models.schemas.roles import RolesInResponse
from services.authentication import get_current_admin_user, get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin

workspaces_users_admin_router = APIRouter(dependencies=[Depends(get_current_admin_user)])
workspaces_users_shared_router = APIRouter(dependencies=[Depends(get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin)])


@workspaces_users_shared_router.get("/workspaces/{workspace_id}/users", response_model=UsersInResponse, name=strings.API_GET_WORKSPACE_USERS)
async def get_workspace_users(workspace=Depends(get_workspace_by_id_from_path)) -> UsersInResponse:
    access_service = get_access_service()
    users = access_service.get_workspace_users(workspace)
    return UsersInResponse(users=users)


@workspaces_users_admin_router.get("/workspaces/{workspace_id}/assignable-users", response_model=AssignableUsersInResponse, name=strings.API_GET_ASSIGNABLE_USERS)
async def get_assignable_users(filter: str = "", maxResultCount: int = 5, workspace=Depends(get_workspace_by_id_from_path)) -> AssignableUsersInResponse:
    access_service = get_access_service()
    assignable_users = access_service.get_assignable_users(filter, maxResultCount)
    return AssignableUsersInResponse(assignable_users=assignable_users)


@workspaces_users_admin_router.get("/workspaces/{workspace_id}/roles", response_model=RolesInResponse, name=strings.API_GET_WORKSPACE_ROLES)
async def get_workspace_roles(workspace=Depends(get_workspace_by_id_from_path)) -> RolesInResponse:
    access_service = get_access_service()
    roles = access_service.get_workspace_roles(workspace)
    return RolesInResponse(roles=roles)


@workspaces_users_admin_router.post("/workspaces/{workspace_id}/users/assign", status_code=status.HTTP_202_ACCEPTED, name=strings.API_ASSIGN_WORKSPACE_USER)
async def assign_workspace_user(response: Response, user_email: str, role_name: str, workspace=Depends(get_workspace_by_id_from_path)) -> UsersInResponse:
    access_service = get_access_service()

    user = access_service.get_user_by_email(user_email)
    role = access_service.get_workspace_role_by_name(role_name, workspace)

    access_service.assign_workspace_user(
        user,
        workspace,
        role
    )

    users = access_service.get_workspace_users(workspace)
    return UsersInResponse(users=users)


@workspaces_users_admin_router.delete("/workspaces/{workspace_id}/users/assign", status_code=status.HTTP_202_ACCEPTED, name=strings.API_REMOVE_WORKSPACE_USER_ASSIGNMENT)
async def remove_workspace_user_assignment(user_email: str,
                                           role_name: str,
                                           workspace=Depends(get_workspace_by_id_from_path)) -> UsersInResponse:

    access_service = get_access_service()

    user = access_service.get_user_by_email(user_email)
    role = access_service.get_workspace_role_by_name(role_name, workspace)

    access_service.remove_workspace_role_user_assignment(
        user,
        role,
        workspace
    )

    users = access_service.get_workspace_users(workspace)
    return UsersInResponse(users=users)
