import asyncio
from fastapi import APIRouter, Request
from core import credentials
from models.schemas.status import HealthCheck, ServiceStatus, StatusEnum
from resources import strings
from services.health_checker import create_airlock_consumer_status, create_deployment_consumer_status, create_resource_processor_status, create_state_store_status, create_service_bus_status
from services.logging import logger

router = APIRouter()


@router.get("/health", name=strings.API_GET_HEALTH_STATUS)
async def health_check(request: Request) -> HealthCheck:
    # The health endpoint checks the status of key components of the system.
    # Note that Resource Processor checks incur Azure management calls, so
    # calling this endpoint frequently may result in API throttling.
    deployment_consumer = getattr(request.app.state, 'deployment_status_updater', None)
    airlock_consumer = getattr(request.app.state, 'airlock_status_updater', None)

    async with credentials.get_credential_async_context() as credential:
        cosmos, sb, rp, deploy, airlock = await asyncio.gather(
            create_state_store_status(),
            create_service_bus_status(credential),
            create_resource_processor_status(credential),
            create_deployment_consumer_status(deployment_consumer),
            create_airlock_consumer_status(airlock_consumer),
        )

    services = [
        ServiceStatus(service=strings.COSMOS_DB, status=cosmos[0], message=cosmos[1]),
        ServiceStatus(service=strings.SERVICE_BUS, status=sb[0], message=sb[1]),
        ServiceStatus(service=strings.RESOURCE_PROCESSOR, status=rp[0], message=rp[1]),
        ServiceStatus(service=strings.DEPLOYMENT_STATUS_CONSUMER, status=deploy[0], message=deploy[1]),
        ServiceStatus(service=strings.AIRLOCK_STATUS_CONSUMER, status=airlock[0], message=airlock[1]),
    ]

    for svc in services:
        if svc.status == StatusEnum.not_ok:
            logger.error(f'{svc.service} Status: {svc.status}, message: {svc.message}')

    return HealthCheck(services=services)
