from fastapi import HTTPException, status

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
        auth_config = {"app_id": app_id}
        return access_service.extract_workspace_auth_information(auth_config)
    except AuthConfigValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def get_access_service(provider: str = AuthProvider.AAD) -> AccessService:
    if provider == AuthProvider.AAD:
        return AADAccessService()
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.INVALID_AUTH_PROVIDER)


get_current_tre_user: User = AzureADAuthorization(app_reg_id=config.API_AUDIENCE, require_one_of_roles=["TREUser"])

get_current_admin_user: User = AzureADAuthorization(app_reg_id=config.API_AUDIENCE, require_one_of_roles=["TREAdmin"])

get_current_workspace_owner_user: User = AzureADAuthorization(require_one_of_roles=["WorkspaceOwner"])

get_current_workspace_researcher_user: User = AzureADAuthorization(require_one_of_roles=["WorkspaceResearcher"])

get_current_workspace_owner_or_researcher_user: User = AzureADAuthorization(require_one_of_roles=["WorkspaceOwner", "WorkspaceResearcher"])
