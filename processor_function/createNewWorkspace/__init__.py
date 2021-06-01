import logging
import json

import azure.functions as func

from shared import cnab_builder


def main(msg: func.ServiceBusMessage):
    try:
        cnab_builder.MESSAGE = json.loads(msg.get_body().decode('utf-8'))
        cnab_builder.deploy_aci()
    except Exception:
        logging.error("CNAB ACI provisioning failed")
