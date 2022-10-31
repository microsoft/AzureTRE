from fastapi import APIRouter
from resources import strings
from _version import __version__
from core import config
from models.schemas.metadata import Metadata

router = APIRouter()


@router.get("/.metadata", name=strings.API_GET_PING)
def metadata() -> Metadata:
    return Metadata(
        api_version=__version__,
        api_client_id=config.API_CLIENT_ID,
        api_root_scope=config.API_ROOT_SCOPE,
        aad_tenant_id=config.AAD_TENANT_ID
    )
