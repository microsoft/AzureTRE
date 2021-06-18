import json
import logging
import os

import azure.functions as func

from opencensus.ext.azure.log_exporter import AzureLogHandler
from shared.cnab_builder import CNABBuilder
from shared.service_bus import ServiceBus
from resources import strings


def initialize_logging(logging_level: int):
    """
    Adds the Application Insights handler for the root logger and sets the given logging level.

    :param logging_level: The logging level to set e.g., logging.WARNING.
    """
    logger = logging.getLogger()
    app_insights_instrumentation_key = os.getenv("APP_INSIGHTS_INSTRUMENTATION_KEY")

    try:
        logger.addHandler(AzureLogHandler(connection_string=f"InstrumentationKey={app_insights_instrumentation_key}"))
    except ValueError:
        logger.error("Application Insights instrumentation key missing")

    logging.basicConfig(level=logging_level)
    logger.setLevel(logging_level)


def main(msg: func.ServiceBusMessage):
    initialize_logging(logging.INFO)
    service_bus = ServiceBus()
    id = ""

    
    resource_request_message = json.loads(msg.get_body().decode('utf-8'))
    id = resource_request_message['id']
    cnab_builder = CNABBuilder(resource_request_message)
    cnab_builder.deploy_aci()

