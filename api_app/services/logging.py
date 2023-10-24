import logging
import os
import re
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from fastapi import FastAPI

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
    "azure.servicebus.aio._base_handler_async",
    "azure.servicebus._pyamqp.aio._connection_async",
    "azure.servicebus._pyamqp.aio._link_async",
    "opentelemetry.attributes"
]


debug = os.environ.get("DEBUG", "False").lower() in ("true", "1")


def configure_loggers():

    for logger_name in UNWANTED_LOGGERS:
        logging.getLogger(logger_name).disabled = True

    for logger_name in LOGGERS_FOR_ERRORS_ONLY:
        logging.getLogger(logger_name).setLevel(logging.ERROR)


def initialize_logging(logging_level: int, add_console_handler: bool, application: FastAPI) -> logging.Logger:

    logger = logging.getLogger()
    logger.setLevel(logging_level)

    if add_console_handler:
        console_formatter = logging.Formatter(
            fmt="%(module)-7s %(name)-7s %(process)-7s %(asctime)s %(otelServiceName)-7s %(otelTraceID)-7s %(otelSpanID)-7s %(levelname)-7s %(message)s"
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    try:
        configure_azure_monitor()
    except ValueError as e:
        logger.error(f"Failed to set Application Insights logger handler: {e}")

    LoggingInstrumentor().instrument(
        set_logging_format=True,
        level=logging_level
    )

    FastAPIInstrumentor.instrument_app(application)
    RequestsInstrumentor().instrument()

    return logger


def shell_output_logger(
    console_output: str,
    prefix_item: str,
    logger: logging.LoggerAdapter,
    logging_level: int,
):

    if not console_output:
        logging.debug("shell console output is empty.")
        return

    console_output = console_output.strip()

    if (
        logging_level != logging.INFO
        and len(console_output) < 200
        and console_output.startswith("Unable to find image '")
        and console_output.endswith("' locally")
    ):
        logging.debug("Image not present locally, setting log to INFO.")
        logging_level = logging.INFO

    logger.log(logging_level, f"{prefix_item} {console_output}")


class AzureLogFormatter(logging.Formatter):
    # 7-bit C1 ANSI sequences
    ansi_escape = re.compile(
        r"""
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by a control sequence
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    """,
        re.VERBOSE,
    )

    MAX_MESSAGE_LENGTH = 32000
    TRUNCATION_TEXT = "MESSAGE TOO LONG, TAILING..."

    def format(self, record):
        s = super().format(record)
        s = AzureLogFormatter.ansi_escape.sub("", s)

        # not doing this here might produce errors if we try to log empty strings.
        if s == "":
            s = "EMPTY MESSAGE!"

        # azure monitor is limiting the message size.
        if len(s) > AzureLogFormatter.MAX_MESSAGE_LENGTH:
            s = f"{AzureLogFormatter.TRUNCATION_TEXT}\n{s[-1 * AzureLogFormatter.MAX_MESSAGE_LENGTH:]}"

        return s
