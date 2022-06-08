import logging

import azure.functions as func
import datetime
import uuid
import json
import re


def main(msg: func.ServiceBusMessage,
         outputEvent: func.Out[func.EventGridOutputEvent]):

    logging.info("Python ServiceBus topic trigger processed message - A new blob was created!.")
    body = msg.get_body().decode('utf-8')
    logging.info('Python ServiceBus queue trigger processed message: %s', body)

    json_body = json.loads(body)
    # message is due to blob creation in an 'in-progress' blob
    if "stalipim" in json_body["topic"]:
        completed_step = "submitted"
        new_status = "in-progress"
        request_id = re.search(r'/blobServices/default/containers/(.*?)/blobs', json_body["subject"]).group(1)

        # Todo delete old container here
        # https://github.com/microsoft/AzureTRE/issues/1963

        # reply with a step completed event
        outputEvent.set(
            func.EventGridOutputEvent(
                id=str(uuid.uuid4()),
                data={"completed_step": completed_step, "new_status": new_status, "request_id": request_id},
                subject=request_id,
                event_type="Airlock.StepResult",
                event_time=datetime.datetime.utcnow(),
                data_version="1.0"))
