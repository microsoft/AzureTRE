import logging
import os
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry import trace
from azure.monitor.opentelemetry import configure_azure_monitor

UNWANTED_LOGGERS = [
    "azure.core.pipeline.policies.http_logging_policy",
    "azure.eventhub._eventprocessor.event_processor",
    # suppressing, have support case open
    "azure.servicebus._pyamqp.aio._session_async",
    "azure.identity.aio._credentials.managed_identity",
    "azure.identity.aio._credentials.environment",
    "azure.identity.aio._internal.get_token_mixin",
    "azure.identity.aio._internal.decorators",
    "azure.identity.aio._credentials.chained",
    "azure.identity",
    "msal.token_cache",
    # Remove these once the following PR is merged:
    # https://github.com/Azure/azure-sdk-for-python/pull/30832
    # Issue: https://github.com/microsoft/AzureTRE/issues/3766
    "azure.servicebus._pyamqp.aio._session_async"
]

LOGGERS_FOR_ERRORS_ONLY = [
    "uamqp",
    "uamqp.authentication.cbs_auth_async",
    "uamqp.async_ops.client_async",
    "uamqp.async_ops.connection_async",
    "uamqp.async_ops",
    "uamqp.authentication",
    "uamqp.c_uamqp",
    "uamqp.connection",
    "uamqp.receiver",
    "uamqp.async_ops.session_async",
    "uamqp.sender",
    "uamqp.client",
    "azure.servicebus.aio._base_handler_async",
    "azure.monitor.opentelemetry.exporter.export._base",
    "azure.servicebus.aio._base_handler_async",
    "azure.servicebus._pyamqp.aio._connection_async",
    "azure.servicebus._pyamqp.aio._link_async",
    "opentelemetry.attributes",
    "azure.servicebus._pyamqp.aio._management_link_async",
    "azure.servicebus._pyamqp.aio._cbs_async",
    "azure.servicebus._pyamqp.aio._client_async"
]

logger = logging.getLogger("azuretre_resource_processor")
tracer = trace.get_tracer("azuretre_resource_processor")


def configure_loggers():
    for logger_name in LOGGERS_FOR_ERRORS_ONLY:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    for logger_name in UNWANTED_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def initialize_logging() -> logging.Logger:

    configure_loggers()

    # Resource Processor has no way to change the logging level, so we set it to INFO
    logging_level = logging.INFO

    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        configure_azure_monitor(
            logger_name="azuretre_resource_processor",
            instrumentation_options={
                "azure_sdk": {"enabled": False},
                "flask": {"enabled": False},
                "django": {"enabled": False},
                "fastapi": {"enabled": True},
                "psycopg2": {"enabled": False},
            }
        )

    LoggingInstrumentor().instrument(
        set_logging_format=True,
        log_level=logging_level,
        tracer_provider=tracer._real_tracer
    )

    return logger


def shell_output_logger(console_output: str, prefix_item: str, logging_level: int):
    """
    Logs the shell output (stdout/err) a line at a time with an option to remove ANSI control chars.
    """
    if not console_output:
        logger.debug("shell console output is empty.")
        return

    console_output = console_output.strip()

    if (logging_level != logging.INFO
            and len(console_output) < 200
            and console_output.startswith("Unable to find image '")
            and console_output.endswith("' locally")):
        logger.debug("Image not present locally, setting log to INFO.")
        logging_level = logging.INFO

    logger.log(logging_level, f"{prefix_item} {console_output}")
