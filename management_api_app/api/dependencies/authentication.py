from fastapi import HTTPException, status

from models.schemas.workspace import AuthenticationConfiguration, AuthProvider
from resources import strings
from services.aad_access_service import AADAccessService
from services.access_service import AccessService, AuthConfigValidationError


def extract_auth_information(auth_config: AuthenticationConfiguration) -> dict:
    access_service = get_access_service(auth_config.provider)
    try:
        return access_service.extract_workspace_auth_information(auth_config.data)
    except AuthConfigValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def get_access_service(provider: str) -> AccessService:
    if provider == AuthProvider.AAD:
        return AADAccessService()
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.INVALID_AUTH_PROVIDER)
