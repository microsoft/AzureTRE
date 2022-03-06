from fastapi import APIRouter

from models.schemas.status import HealthCheck, ServiceStatus
from resources import strings
from services.health_checker import create_state_store_status, create_service_bus_status


router = APIRouter()


@router.get("/status", name=strings.API_GET_STATUS_OF_SERVICES)
async def health_check() -> HealthCheck:
    cosmos_status, cosmos_message = create_state_store_status()
    sb_status, sb_message = await create_service_bus_status()
    services = [ServiceStatus(service=strings.COSMOS_DB, status=cosmos_status, message=cosmos_message),
                ServiceStatus(service=strings.SERVICE_BUS, status=sb_status, message=sb_message)]
    return HealthCheck(services=services)
