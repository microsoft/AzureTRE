import logging

import azure.functions as func
import json

from shared_code import blob_operations
from pydantic import BaseModel, parse_obj_as


class ToDeleteProperties(BaseModel):
    account_rg: str
    account_name: str
    request_id: str


def main(msg: func.ServiceBusMessage):
    body = msg.get_body().decode('utf-8')
    logging.info(f'Python ServiceBus queue trigger processed mesage: {body}')

    storage_client = blob_operations.get_storage_management_client()

    json_body = json.loads(body)
    logging.info(f'Going to remove the blob {}... when i get round to it')
