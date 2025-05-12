import logging

import azure.functions as func
import datetime
import uuid
import json
import os
from shared_code import constants, blob_operations, parsers


def main(msg: func.ServiceBusMessage,
         outputEvent: func.Out[func.EventGridOutputEvent]):

    logging.info("Python ServiceBus queue trigger processed message - Malware scan result arrived!")
    body = msg.get_body().decode('utf-8')
    logging.info(f'Python ServiceBus queue trigger processed message: {body}')
    status_message = None

    try:
        enable_malware_scanning = parsers.parse_bool(os.environ["ENABLE_MALWARE_SCANNING"])
    except KeyError as e:
        logging.error("environment variable 'ENABLE_MALWARE_SCANNING' does not exists. cannot continue.")
        raise e

    # Sanity
    if not enable_malware_scanning:
        # A scan result arrived despite the fact malware scanning should be disabled. This may result in unexpected behaviour.
        # Raise an exception and stop
        error_msg = "Malware scanning is disabled, however a malware scan result arrived. Ignoring it."
        logging.error(error_msg)
        raise Exception(error_msg)

    try:
        json_body = json.loads(body)
        blob_uri = json_body["data"]["blobUri"]
        verdict = json_body["data"]["scanResultType"]
    except KeyError as e:
        logging.error("body was not as expected {}", e)
        raise e

    # Extract request id
    _, request_id, _ = blob_operations.get_blob_info_from_blob_url(blob_url=blob_uri)

    # If clean, we can continue and move the request to the review stage
    # Otherwise, move the request to the blocked stage
    completed_step = constants.STAGE_SUBMITTED
    if verdict == constants.NO_THREATS:
        logging.info(f'No malware were found in request id {request_id}, moving to {constants.STAGE_IN_REVIEW} stage')
        new_status = constants.STAGE_IN_REVIEW
    else:
        logging.info(f'Malware was found in request id {request_id}, moving to {constants.STAGE_BLOCKING_INPROGRESS} stage')
        new_status = constants.STAGE_BLOCKING_INPROGRESS
        status_message = verdict

    # Send the event to indicate this step is done (and to request a new status change)
    outputEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"completed_step": completed_step, "new_status": new_status, "request_id": request_id, "status_message": status_message},
            subject=request_id,
            event_type="Airlock.StepResult",
            event_time=datetime.datetime.utcnow(),
            data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))
