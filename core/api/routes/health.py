from fastapi import APIRouter
from api.models.schemas.health import HealthCheck, ServiceStatus
from api.resources import strings
from api.services.health_checker import get_state_store_status


router = APIRouter()


@router.get("", name="health:get-status-of-services")
async def health_check() -> HealthCheck:
    status, message = get_state_store_status()
    services = [ServiceStatus(service=strings.COSMOS_DB, status=status, message=message)]
    return HealthCheck(services=services)
