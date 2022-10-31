import logging
import os
import re

from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace import config_integration
from opencensus.trace.samplers import AlwaysOnSampler
from opencensus.trace.tracer import Tracer

from shared.config import VERSION

UNWANTED_LOGGERS = [
    "azure.core.pipeline.policies.http_logging_policy",
    "azure.eventhub._eventprocessor.event_processor",
    "azure.identity.aio._credentials.managed_identity",
    "azure.identity.aio._credentials.environment",
    "azure.identity.aio._internal.get_token_mixin",
    "azure.identity.aio._internal.decorators",
    "azure.identity.aio._credentials.chained",
    "azure.identity",
    "msal.token_cache"
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
    "azure.servicebus.aio._base_handler_async"
]

debug = os.environ.get('DEBUG', 'False').lower() in ('true', '1')


def disable_unwanted_loggers():
    """
    Disables the unwanted loggers.
    """
    for logger_name in UNWANTED_LOGGERS:
        logging.getLogger(logger_name).disabled = True


def telemetry_processor_callback_function(envelope):
    envelope.tags['ai.cloud.role'] = 'resource_processor'
    envelope.tags['ai.application.ver'] = VERSION


def initialize_logging(logging_level: int, correlation_id: str, add_console_handler: bool = False) -> logging.LoggerAdapter:
    """
    Adds the Application Insights handler for the root logger and sets the given logging level.
    Creates and returns a logger adapter that integrates the correlation ID, if given, to the log messages.
    Note: This should be called only once, otherwise duplicate log entries could be produced.

    :param logging_level: The logging level to set e.g., logging.WARNING.
    :param correlation_id: Optional. The correlation ID that is passed on to the operation_Id in App Insights.
    :returns: A newly created logger adapter.
    """
    logger = logging.getLogger()

    # When using sessions and NEXT_AVAILABLE_SESSION we see regular exceptions which are actually expected
    # See https://github.com/Azure/azure-sdk-for-python/issues/9402
    # Other log entries such as 'link detach' also confuse the logs, and are expected.
    # We don't want these making the logs any noisier so we raise the logging level for that logger here
    # To inspect all the loggers, use -> loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for logger_name in LOGGERS_FOR_ERRORS_ONLY:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    if add_console_handler:
        console_formatter = logging.Formatter(fmt='%(module)-7s %(name)-7s %(process)-7s %(asctime)s %(levelname)-7s %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    try:
        # picks up APPLICATIONINSIGHTS_CONNECTION_STRING automatically
        azurelog_handler = AzureLogHandler()
        azurelog_handler.add_telemetry_processor(telemetry_processor_callback_function)
        azurelog_formatter = AzureLogFormatter()
        azurelog_handler.setFormatter(azurelog_formatter)
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


def get_message_id_logger(correlation_id: str) -> logging.LoggerAdapter:
    """
    Gets a logger that includes message id for easy correlation between log entries.
    :param correlation_id: Optional. The correlation ID that is passed on to the operation_Id in App Insights.
    :returns: A modified logger adapter (from the original initiated one).
    """
    logger = logging.getLogger()
    extra = None

    if correlation_id:
        extra = {'traceId': correlation_id}

    adapter = logging.LoggerAdapter(logger, extra)
    adapter.debug(f"Logger adapter now includes extra: {extra}")

    return adapter


def shell_output_logger(console_output: str, prefix_item: str, logger: logging.LoggerAdapter, logging_level: int):
    """
    Logs the shell output (stdout/err) a line at a time with an option to remove ANSI control chars.
    """
    if not console_output:
        logging.debug("shell console output is empty.")
        return

    console_output = console_output.strip()

    if (logging_level != logging.INFO
            and len(console_output) < 200
            and console_output.startswith("Unable to find image '")
            and console_output.endswith("' locally")):
        logging.debug("Image not present locally, setting log to INFO.")
        logging_level = logging.INFO

    logger.log(logging_level, prefix_item)
    logger.log(logging_level, console_output)


class AzureLogFormatter(logging.Formatter):
    # 7-bit C1 ANSI sequences
    ansi_escape = re.compile(r'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by a control sequence
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    ''', re.VERBOSE)

    MAX_MESSAGE_LENGTH = 32000
    TRUNCATION_TEXT = "MESSAGE TOO LONG, TAILING..."

    def format(self, record):
        s = super().format(record)
        s = AzureLogFormatter.ansi_escape.sub('', s)

        # not doing this here might produce errors if we try to log empty strings.
        if (s == ''):
            s = "EMPTY MESSAGE!"

        # azure monitor is limiting the message size.
        if (len(s) > AzureLogFormatter.MAX_MESSAGE_LENGTH):
            s = f"{AzureLogFormatter.TRUNCATION_TEXT}\n{s[-1 * AzureLogFormatter.MAX_MESSAGE_LENGTH:]}"

        return s
