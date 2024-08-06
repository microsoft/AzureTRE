import asyncio
from fastapi import APIRouter, Request
from core import credentials
from models.schemas.status import HealthCheck, ServiceStatus, StatusEnum
from resources import strings
from services.health_checker import create_resource_processor_status, create_state_store_status, create_service_bus_status
from services.logging import logger

router = APIRouter()


@router.get("/health", name=strings.API_GET_HEALTH_STATUS)
async def health_check(request: Request) -> HealthCheck:
    # The health endpoint checks the status of key components of the system.
    # Note that Resource Processor checks incur Azure management calls, so
    # calling this endpoint frequently may result in API throttling.
    async with credentials.get_credential_async_context() as credential:
        cosmos, sb, rp = await asyncio.gather(
            create_state_store_status(),
            create_service_bus_status(credential),
            create_resource_processor_status(credential)
        )
    cosmos_status, cosmos_message = cosmos
    sb_status, sb_message = sb
    rp_status, rp_message = rp
    if cosmos_status == StatusEnum.not_ok or sb_status == StatusEnum.not_ok or rp_status == StatusEnum.not_ok:
        logger.error(f'Cosmos Status: {cosmos_status}, message: {cosmos_message}')
        logger.error(f'Service Bus Status: {sb_status}, message: {sb_message}')
        logger.error(f'Resource Processor Status: {rp_status}, message: {rp_message}')

    services = [ServiceStatus(service=strings.COSMOS_DB, status=cosmos_status, message=cosmos_message),
                ServiceStatus(service=strings.SERVICE_BUS, status=sb_status, message=sb_message),
                ServiceStatus(service=strings.RESOURCE_PROCESSOR, status=rp_status, message=rp_message)]

    return HealthCheck(services=services)
