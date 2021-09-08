from fastapi import APIRouter

from models.schemas.status import HealthCheck, ServiceStatus
from resources import strings
from services.health_checker import create_state_store_status


router = APIRouter()


@router.get("/status", name=strings.API_GET_STATUS_OF_SERVICES)
async def health_check() -> HealthCheck:
    status, message = create_state_store_status()
    services = [ServiceStatus(service=strings.COSMOS_DB, status=status, message=message)]
    return HealthCheck(services=services)
