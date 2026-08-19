import logging

import azure.functions as func
import datetime
import uuid
import json
import os
from shared_code import constants, blob_operations, parsers, airlock_storage_helper


def main(msg: func.ServiceBusMessage,
         outputEvent: func.Out[func.EventGridOutputEvent]):

    logging.info("Python ServiceBus queue trigger processed message - Malware scan result arrived!")
    body = msg.get_body().decode('utf-8')
    logging.info(f'Python ServiceBus queue trigger processed message: {body}')

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
    account_name, container_name, blob_name = blob_operations.get_blob_info_from_blob_url(blob_url=blob_uri)
    request_id = airlock_storage_helper.get_request_id_from_container_name(container_name)

    # Consolidated destination copies must not emit duplicate scan results. The container name
    # identifies the original upload, so the source blob is not read - it may already be sealed away.
    if account_name.startswith(constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE) and not container_name.endswith(constants.DRAFT_CONTAINER_SUFFIX):
        logging.info(f'Scan result for copied blob in request {request_id} ignored; only the original upload gates submission.')
        return

    # The verdict is reported as a fact; the API decides the status once submission is validated.
    outputEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"completed_step": constants.STAGE_SUBMITTED, "request_id": request_id,
                  "scan_result": {"clean": verdict == constants.NO_THREATS, "message": None if verdict == constants.NO_THREATS else verdict}},
            subject=request_id,
            event_type="Airlock.StepResult",
            event_time=datetime.datetime.now(datetime.UTC),
            data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))
