import asyncio
import logging
from opencensus.ext.azure.trace_exporter import AzureExporter
import os
import uvicorn

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import asynccontextmanager

from services.tracing import RequestTracerMiddleware
from opencensus.trace.samplers import ProbabilitySampler

from starlette.exceptions import HTTPException
from starlette.middleware.errors import ServerErrorMiddleware

from api.routes.api import router as api_router
from api.errors.http_error import http_error_handler
from api.errors.validation_error import http422_error_handler
from api.errors.generic_error import generic_error_handler
from core import config
from db.events import bootstrap_database
from services.logging import initialize_logging, telemetry_processor_callback_function
from service_bus.deployment_status_updater import DeploymentStatusUpdater
from service_bus.airlock_request_status_update import AirlockStatusUpdater


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.cosmos_client = None

    while not await bootstrap_database(app):
        await asyncio.sleep(5)
        logging.warning("Database connection could not be established")

    deploymentStatusUpdater = DeploymentStatusUpdater(app)
    await deploymentStatusUpdater.init_repos()

    airlockStatusUpdater = AirlockStatusUpdater(app)
    await airlockStatusUpdater.init_repos()

    loop = asyncio.get_event_loop()
    coroutines = [deploymentStatusUpdater.receive_messages(), airlockStatusUpdater.receive_messages()]
    loop.create_task(asyncio.wait(coroutines))

    yield


def get_application() -> FastAPI:
    application = FastAPI(
        title=config.PROJECT_NAME,
        debug=config.DEBUG,
        description=config.API_DESCRIPTION,
        version=config.VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan
    )

    try:
        if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
            exporter = AzureExporter(sampler=ProbabilitySampler(1.0))
            exporter.add_telemetry_processor(telemetry_processor_callback_function)
            application.add_middleware(RequestTracerMiddleware, exporter=exporter)
    except Exception:
        logging.exception("Failed to add RequestTracerMiddleware")

    application.add_middleware(ServerErrorMiddleware, handler=generic_error_handler)
    # Allow local UI debugging with local API
    if config.ENABLE_LOCAL_DEBUGGING:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"])

    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, http422_error_handler)

    application.include_router(api_router)
    return application


if config.DEBUG:
    initialize_logging(logging.DEBUG, add_console_handler=True)
else:
    initialize_logging(logging.INFO, add_console_handler=False)

app = get_application()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, loop="asyncio")
