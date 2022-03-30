from fastapi import APIRouter
from models.schemas.status import HealthCheck, ServiceStatus, StatusEnum
from resources import strings
from services.health_checker import create_resource_processor_status, create_state_store_status, create_service_bus_status
from fastapi import HTTPException, status

router = APIRouter()


@router.get("/health", name=strings.API_GET_HEALTH_STATUS)
async def health_check() -> HealthCheck:
    cosmos_status, cosmos_message = create_state_store_status()
    sb_status, sb_message = await create_service_bus_status()
    rp_status, rp_message = create_resource_processor_status()
    services = [ServiceStatus(service=strings.COSMOS_DB, status=cosmos_status, message=cosmos_message),
                ServiceStatus(service=strings.SERVICE_BUS, status=sb_status, message=sb_message),
                ServiceStatus(service=strings.RESOURCE_PROCESSOR, status=rp_status, message=rp_message)]
    health_check_result = HealthCheck(services=services)
    if cosmos_status == StatusEnum.not_ok or sb_status == StatusEnum.not_ok or rp_status == StatusEnum.not_ok:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_check_result.json())
    return health_check_result
