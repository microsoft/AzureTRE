import logging

import azure.functions as func
import datetime


def main(msg: func.ServiceBusMessage,
         outputEvent: func.Out[func.EventGridOutputEvent]):

    logging.info('Python ServiceBus queue trigger processed message: %s', msg.get_body().decode('utf-8'))
    outputEvent.set(
        func.EventGridOutputEvent(
            id="step-result-id",
            data={"tag1": "value1", "tag2": "value2"},
            subject="test-subject",
            event_type="test-event-1",
            event_time=datetime.datetime.utcnow(),
            data_version="1.0"))
