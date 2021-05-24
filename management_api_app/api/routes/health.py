from fastapi import APIRouter
from models.schemas.health import HealthCheck, ServiceStatus
from resources import strings
from services.health_checker import create_state_store_status


router = APIRouter()


@router.get("/health", name="health:get-status-of-services")
async def health_check() -> HealthCheck:
    status, message = create_state_store_status()
    services = [ServiceStatus(service=strings.COSMOS_DB, status=status, message=message)]
    return HealthCheck(services=services)
