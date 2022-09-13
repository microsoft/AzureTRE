import asyncio
import logging
from fastapi import APIRouter
from core import credentials
from models.schemas.status import HealthCheck, ServiceStatus, StatusEnum
from resources import strings
from services.health_checker import create_resource_processor_status, create_state_store_status, create_service_bus_status


router = APIRouter()


@router.get("/health", name=strings.API_GET_HEALTH_STATUS)
@router.get("/", name=strings.API_GET_HEALTH_STATUS)
async def health_check() -> HealthCheck:
    async with credentials.get_credential_async() as credential:
        cosmos, sb, rp = await asyncio.gather(
            create_state_store_status(credential),
            create_service_bus_status(credential),
            create_resource_processor_status(credential)
        )
    if cosmos[0] == StatusEnum.not_ok or sb[0] == StatusEnum.not_ok or rp[0] == StatusEnum.not_ok:
        logging.error(f'Cosmos Status: {cosmos[0]}, message: {cosmos[1]}')
        logging.error(f'Service Bus Status: {sb[0]}, message: {sb[1]}')
        logging.error(f'Resource Processor Status: {rp[0]}, message: {rp[1]}')

    services = [ServiceStatus(service=strings.COSMOS_DB, status=StatusEnum.ok, message=""),
                ServiceStatus(service=strings.SERVICE_BUS, status=StatusEnum.ok, message=""),
                ServiceStatus(service=strings.RESOURCE_PROCESSOR, status=StatusEnum.ok, message="")]

    return HealthCheck(services=services)
