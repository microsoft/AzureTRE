import logging
import os
import uvicorn

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi_utils.tasks import repeat_every
from starlette.exceptions import HTTPException
from starlette.middleware.errors import ServerErrorMiddleware

from api.routes.api import router as api_router
from api.routes.api import tags_metadata
from api.errors.http_error import http_error_handler
from api.errors.validation_error import http422_error_handler
from api.errors.generic_error import generic_error_handler
from core import config
from core.events import create_start_app_handler, create_stop_app_handler
from services.logging import disable_unwanted_loggers, initialize_logging
from service_bus.deployment_status_update import receive_message_and_update_deployment

# Opencensus Azure imports
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.attributes_helper import COMMON_ATTRIBUTES
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.span import SpanKind
from opencensus.trace.tracer import Tracer

HTTP_HOST = COMMON_ATTRIBUTES["HTTP_HOST"]
HTTP_METHOD = COMMON_ATTRIBUTES["HTTP_METHOD"]
HTTP_PATH = COMMON_ATTRIBUTES["HTTP_PATH"]
HTTP_ROUTE = COMMON_ATTRIBUTES["HTTP_ROUTE"]
HTTP_URL = COMMON_ATTRIBUTES["HTTP_URL"]
HTTP_STATUS_CODE = COMMON_ATTRIBUTES["HTTP_STATUS_CODE"]


def get_application() -> FastAPI:
    application = FastAPI(
        title=config.PROJECT_NAME,
        debug=config.DEBUG,
        description=config.API_DESCRIPTION,
        version=config.VERSION,
        docs_url="/api/docs",
        swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect",
        swagger_ui_init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
            "clientId": config.SWAGGER_UI_CLIENT_ID,
            "scopes": ["openid", "offline_access", f"api://{config.API_CLIENT_ID}/Workspace.Read", f"api://{config.API_CLIENT_ID}/Workspace.Write"]
        },
        openapi_tags=tags_metadata
    )

    application.add_event_handler("startup", create_start_app_handler(application))
    application.add_event_handler("shutdown", create_stop_app_handler(application))

    application.add_middleware(ServerErrorMiddleware, handler=generic_error_handler)
    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, http422_error_handler)

    application.include_router(api_router, prefix=config.API_PREFIX)
    return application


app = get_application()


def get_log_exporter():
    try:
        exporter = AzureExporter(connection_string=f'InstrumentationKey={os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")}', sampler=ProbabilitySampler(1.0))
        return exporter
    except ValueError as e:
        logging.error(f"Failed to create Application Insights log exporter: {e}")


@app.on_event("startup")
async def initialize_logging_on_startup():
    if config.DEBUG:
        initialize_logging(logging.DEBUG)
    else:
        initialize_logging(logging.INFO)

    disable_unwanted_loggers()


@app.on_event("startup")
@repeat_every(seconds=20, wait_first=True, logger=logging.getLogger())
async def update_deployment_status() -> None:
    await receive_message_and_update_deployment(app)


exporter = get_log_exporter()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    tracer = Tracer(exporter=exporter)

    with tracer.span("main") as span:
        span.span_kind = SpanKind.SERVER

        tracer.add_attribute_to_current_span(HTTP_HOST, request.url.hostname)
        tracer.add_attribute_to_current_span(HTTP_METHOD, request.method)
        tracer.add_attribute_to_current_span(HTTP_PATH, request.url.path)
        tracer.add_attribute_to_current_span(HTTP_ROUTE, request.url.path)
        tracer.add_attribute_to_current_span(HTTP_URL, str(request.url))

        response = await call_next(request)
        tracer.add_attribute_to_current_span(HTTP_STATUS_CODE, response.status_code)
    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
