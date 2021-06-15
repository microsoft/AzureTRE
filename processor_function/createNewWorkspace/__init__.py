import logging
import json

import azure.functions as func

from shared.cnab_builder import CNABBuilder


def main(msg: func.ServiceBusMessage):
    try:
        resource_request_message = json.loads(msg.get_body().decode('utf-8'))
        cnab_builder = CNABBuilder(resource_request_message)
        cnab_builder.deploy_aci()
    except Exception:
        logging.error("CNAB ACI provisioning failed")