import json
import logging
import os

import azure.functions as func

from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace import config_integration

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

    config_integration.trace_integrations(['logging'])
    logging.basicConfig(level=logging_level, format='correlationId=%(correlationId)s %(message)s')
    logger.setLevel(logging_level)


def main(msg: func.ServiceBusMessage):
    service_bus = ServiceBus()
    id = ""
    logging_properties = { "correlationId": f"{msg.correlation_id}" }
    initialize_logging(logging.INFO)

    try:
        resource_request_message = json.loads(msg.get_body().decode('utf-8'))
        logging.info(f"Received resource request message: {resource_request_message}", extra=logging_properties)
        id = resource_request_message['id']
        cnab_builder = CNABBuilder(resource_request_message)
        cnab_builder.deploy_aci()
    except Exception:
        service_bus.send_status_update_message(id, strings.RESOURCE_STATUS_DEPLOYMENT_FAILED, strings.UNKNOWN_EXCEPTION)
        logging.error("CNAB ACI provisioning failed")
