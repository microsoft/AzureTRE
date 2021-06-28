from fastapi import Depends, HTTPException, status

from models.schemas.workspace import AuthenticationConfiguration, AuthProvider
from resources import strings
from services.aad_authentication import authorize
from services.aad_access_service import AADAccessService
from services.authentication import User
from services.access_service import AccessService, AuthConfigValidationError


def extract_auth_information(auth_config: AuthenticationConfiguration) -> dict:
    access_service = get_access_service(auth_config.provider)
    try:
        return access_service.extract_workspace_auth_information(auth_config.data)
    except AuthConfigValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def get_access_service(provider: str = AuthProvider.AAD) -> AccessService:
    if provider == AuthProvider.AAD:
        return AADAccessService()
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.INVALID_AUTH_PROVIDER)


async def get_current_user(user: User = Depends(authorize)) -> User:
    return user


async def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    if 'TREAdmin' not in user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.AUTH_NOT_ASSIGNED_TO_ADMIN_ROLE, headers={"WWW-Authenticate": "Bearer"})
    return user
