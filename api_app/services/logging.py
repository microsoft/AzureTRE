import logging
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from azure.monitor.opentelemetry import configure_azure_monitor

from core.config import DEBUG

UNWANTED_LOGGERS = [
    "azure.core.pipeline.policies.http_logging_policy",
    "azure.eventhub._eventprocessor.event_processor",
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
    "azure.monitor.opentelemetry.exporter.export._base",
    "azure.servicebus.aio._base_handler_async",
    "azure.servicebus._pyamqp.aio._cbs_async",
    "azure.servicebus._pyamqp.aio._connection_async",
    "azure.servicebus._pyamqp.aio._link_async",
    "azure.servicebus._pyamqp.aio._management_link_async",
    "opentelemetry.attributes",
    "uamqp",
    "uamqp.async_ops",
    "uamqp.async_ops.client_async",
    "uamqp.async_ops.connection_async",
    "uamqp.async_ops.session_async",
    "uamqp.authentication",
    "uamqp.authentication.cbs_auth_async",
    "uamqp.c_uamqp",
    "uamqp.client",
    "uamqp.connection",
    "uamqp.receiver",
    "uamqp.sender",
    "urllib3.connectionpool"
]


logger = logging.getLogger("azuretre_api")


def configure_loggers():
    for logger_name in LOGGERS_FOR_ERRORS_ONLY:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    for logger_name in UNWANTED_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def initialize_logging() -> logging.Logger:

    configure_loggers()

    if DEBUG:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    try:
        configure_azure_monitor(
            logger_name="azuretre",
            instrumentation_options={
                "azure_sdk": {"enabled": True},
                "flask": {"enabled": False},
                "django": {"enabled": False},
                "fastapi": {"enabled": True},
            }
        )
    except ValueError as e:
        logger.error(f"Failed to set Application Insights logger handler: {e}")

    LoggingInstrumentor().instrument(
        set_logging_format=True,
        level=logging_level
    )

    return logger
