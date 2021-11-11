
from fastapi import Depends, HTTPException, status

from core import config

from models.domain.authentication import User
from models.schemas.workspace import AuthProvider
from resources import strings
from services.aad_authentication import AzureADAuthorization
from services.aad_access_service import AADAccessService
from services.access_service import AccessService, AuthConfigValidationError


def extract_auth_information(app_id: str) -> dict:
    access_service = get_access_service('AAD')
    try:
        auth_config = {'app_id': app_id}
        return access_service.extract_workspace_auth_information(auth_config)
    except AuthConfigValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def get_access_service(provider: str = AuthProvider.AAD) -> AccessService:
    if provider == AuthProvider.AAD:
        return AADAccessService()
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.INVALID_AUTH_PROVIDER)


authorize_tre_app = AzureADAuthorization(app_reg_id=config.API_AUDIENCE)

authorize_ws_app = AzureADAuthorization()


async def get_tre_user(user: User = Depends(authorize_tre_app)) -> User:
    return user


async def get_ws_user(user: User = Depends(authorize_ws_app)) -> User:
    return user


async def get_authorized_tre_user(user: User, require_one_of_roles: list = None) -> User:
    print(user)
    if not any(role in require_one_of_roles for role in user.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'{strings.ACCESS_USER_DOES_NOT_HAVE_REQUIRED_ROLE}: {require_one_of_roles}', headers={'WWW-Authenticate': 'Bearer'})
    return user


async def get_authorized_tre_workspace_user(user: User, require_one_of_roles: list = None) -> User:
    if not any(role in require_one_of_roles for role in user.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'{strings.ACCESS_USER_DOES_NOT_HAVE_REQUIRED_ROLE}: {require_one_of_roles}', headers={'WWW-Authenticate': 'Bearer'})
    return user


async def get_current_tre_user(user: User = Depends(get_tre_user)) -> User:
    return await get_authorized_tre_user(user, require_one_of_roles=['TREUser'])


async def get_current_admin_user(user: User = Depends(get_tre_user)) -> User:
    return await get_authorized_tre_user(user, require_one_of_roles=['TREAdmin'])


async def get_current_tre_user_or_tre_admin(user: User = Depends(get_tre_user)) -> User:
    return await get_authorized_tre_user(user, require_one_of_roles=['TREUser', 'TREAdmin'])


async def get_current_workspace_owner_user(user: User = Depends(get_ws_user)) -> User:
    return await get_authorized_tre_workspace_user(user, require_one_of_roles=['WorkspaceOwner'])


async def get_current_workspace_researcher_user(user: User = Depends(get_ws_user)) -> User:
    return await get_authorized_tre_workspace_user(user, require_one_of_roles=['WorkspaceResearcher'])


async def get_current_workspace_owner_or_researcher_user(user: User = Depends(get_ws_user)) -> User:
    return await get_authorized_tre_workspace_user(user, require_one_of_roles=['WorkspaceOwner', 'WorkspaceResearcher'])
