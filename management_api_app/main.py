import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
from opencensus.ext.azure.log_exporter import AzureLogHandler
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError

from api.routes.api import router as api_router
from api.errors.http_error import http_error_handler
from api.errors.validation_error import http422_error_handler
from core.config import API_PREFIX, DEBUG, PROJECT_NAME, VERSION
from core.events import create_start_app_handler, create_stop_app_handler
from service_bus.deployment_status_update import receive_message_and_update_deployment


def get_application() -> FastAPI:
    application = FastAPI(title=PROJECT_NAME, debug=DEBUG, version=VERSION)

    application.add_event_handler("startup", create_start_app_handler(application))
    application.add_event_handler("shutdown", create_stop_app_handler(application))

    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, http422_error_handler)

    application.include_router(api_router, prefix=API_PREFIX)
    return application


def initialize_logging(logging_level : int):
    """
    Adds the Application Insights handler for the root logger and sets the given logging level.

    :param logging_level: The logging level to set e.g., logging.WARNING.
    """
    logger = logging.getLogger()
    app_insights_instrumentation_key = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")

    try:
        logger.addHandler(AzureLogHandler(connection_string=f"InstrumentationKey={app_insights_instrumentation_key}"))
    except ValueError:
        logger.error("Application Insights instrumentation key missing")

    logging.basicConfig(level=logging_level)
    logger.setLevel(logging_level)


if DEBUG:
    initialize_logging(logging.DEBUG)
else:
    initialize_logging(logging.INFO)


app = get_application()


@app.on_event("startup")
@repeat_every(seconds=20, wait_first=True, logger=logging.getLogger())
def update_deployment_status() -> None:
    receive_message_and_update_deployment()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
