import logging
import os
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry import trace
from azure.monitor.opentelemetry import configure_azure_monitor

from core.config import APPLICATIONINSIGHTS_CONNECTION_STRING, LOGGING_LEVEL

# Standard log format with worker ID
LOG_FORMAT = '%(asctime)s - Worker %(worker_id)s - %(name)s - %(levelname)s - %(message)s'

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
    "azure.servicebus._pyamqp.aio._client_async",
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


class WorkerIdFilter(logging.Filter):
    """
    A filter that adds worker_id to all log records.
    """

    def __init__(self):
        super().__init__()
        # Get the process ID as a unique worker identifier
        self.worker_id = os.getpid()

    def filter(self, record: logging.LogRecord) -> bool:
        # Add worker_id as an attribute to the log record
        record.worker_id = self.worker_id
        return True


logger = logging.getLogger("azuretre_api")
tracer = trace.get_tracer("azuretre_api")


def configure_loggers():
    for logger_name in LOGGERS_FOR_ERRORS_ONLY:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    for logger_name in UNWANTED_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def apply_worker_id_to_logger(logger_instance):
    """
    Apply the worker ID filter to a logger instance.
    """
    worker_filter = WorkerIdFilter()
    logger_instance.addFilter(worker_filter)

    # Update handlers to include worker_id in the format
    for handler in logger_instance.handlers:
        if isinstance(handler, logging.StreamHandler):
            formatter = logging.Formatter(LOG_FORMAT)
            handler.setFormatter(formatter)


def initialize_logging() -> logging.Logger:

    configure_loggers()

    logging_level = logging.INFO

    if LOGGING_LEVEL == "INFO":
        logging_level = logging.INFO
    elif LOGGING_LEVEL == "DEBUG":
        logging_level = logging.DEBUG
    elif LOGGING_LEVEL == "WARNING":
        logging_level = logging.WARNING
    elif LOGGING_LEVEL == "ERROR":
        logging_level = logging.ERROR

    if APPLICATIONINSIGHTS_CONNECTION_STRING:
        configure_azure_monitor(
            logger_name="azuretre_api",
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
        tracer_provider=tracer._real_tracer,
        log_format=LOG_FORMAT
    )

    # Set up a handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        logger.addHandler(handler)

    # Apply worker ID filter
    apply_worker_id_to_logger(logger)

    logger.info("Logging initialized with level: %s", LOGGING_LEVEL)

    return logger
