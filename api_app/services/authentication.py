
from services.aad_authentication import AzureADAuthorization, AuthConfigValidationError


def extract_auth_information(workspace_creation_properties: dict) -> dict:
    from fastapi import HTTPException, status
    aad_service = get_aad_service()
    try:
        return aad_service.extract_workspace_auth_information(workspace_creation_properties)
    except AuthConfigValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def get_aad_service() -> AzureADAuthorization:
    """Return an :class:`AzureADAuthorization` instance for Graph API calls."""
    return AzureADAuthorization()
