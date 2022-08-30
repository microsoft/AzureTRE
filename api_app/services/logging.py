import logging

from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace import config_integration
from opencensus.trace.samplers import AlwaysOnSampler
from opencensus.trace.tracer import Tracer

from core.config import VERSION


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
    "uamqp",
    "uamqp.authentication.cbs_auth_async",
    "uamqp.async_ops.client_async",
    "uamqp.async_ops.connection_async",
    "uamqp.async_ops",
    "uamqp.authentication",
    "uamqp.c_uamqp",
    "uamqp.connection",
    "uamqp.receiver"
]


def disable_unwanted_loggers():
    """
    Disables the unwanted loggers.
    """
    for logger_name in UNWANTED_LOGGERS:
        logging.getLogger(logger_name).disabled = True


def telemetry_processor_callback_function(envelope):
    envelope.tags['ai.cloud.role'] = 'api'
    envelope.tags['ai.application.ver'] = VERSION


def initialize_logging(logging_level: int, correlation_id: str = None) -> logging.LoggerAdapter:
    """
    Adds the Application Insights handler for the root logger and sets the given logging level.
    Creates and returns a logger adapter that integrates the correlation ID, if given, to the log messages.

    :param logging_level: The logging level to set e.g., logging.WARNING.
    :param correlation_id: Optional. The correlation ID that is passed on to the operation_Id in App Insights.
    :returns: A newly created logger adapter.
    """
    logger = logging.getLogger()

    try:
        # picks up APPLICATIONINSIGHTS_CONNECTION_STRING automatically
        azurelog_handler = AzureLogHandler()
        azurelog_handler.add_telemetry_processor(telemetry_processor_callback_function)
        logger.addHandler(azurelog_handler)
    except ValueError as e:
        logger.error(f"Failed to set Application Insights logger handler: {e}")

    config_integration.trace_integrations(['logging'])
    logging.basicConfig(level=logging_level, format='%(asctime)s traceId=%(traceId)s spanId=%(spanId)s %(message)s')
    Tracer(sampler=AlwaysOnSampler())
    logger.setLevel(logging_level)

    extra = None

    if correlation_id:
        extra = {'traceId': correlation_id}

    adapter = logging.LoggerAdapter(logger, extra)
    adapter.debug(f"Logger adapter initialized with extra: {extra}")

    return adapter
