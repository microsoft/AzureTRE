import logging
import json


import azure.functions as func

from shared import cnab_builder


def main(msg: func.ServiceBusMessage):
    
    cnab_builder.message = json.loads(msg.get_body().decode('utf-8'))
    
    cnab_builder.deploy_aci()
