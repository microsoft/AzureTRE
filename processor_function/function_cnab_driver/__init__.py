import json
import logging

import azure.functions as func

from shared.cnab_builder import CNABBuilder
from shared.logger import initialize_logging
from shared.service_bus import ServiceBus
from resources import strings


def main(msg: func.ServiceBusMessage):
    logger_adapter = initialize_logging(logging.INFO, msg.correlation_id)
    service_bus = ServiceBus()
    id = ""

    try:
        resource_request_message = json.loads(msg.get_body().decode('utf-8'))
        logger_adapter.info(f"Received resource request message: {resource_request_message}")
        id = resource_request_message['id']
        cnab_builder = CNABBuilder(resource_request_message, logger_adapter)
        cnab_builder.deploy_aci()
    except Exception as e:
        service_bus.send_status_update_message(id, strings.RESOURCE_STATUS_FAILED, strings.UNKNOWN_EXCEPTION)
        logger_adapter.error(f"CNAB ACI provisioning failed: {e}")
