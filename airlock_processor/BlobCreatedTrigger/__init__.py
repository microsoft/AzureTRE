from distutils.util import strtobool
import logging
import datetime
import uuid
import json
import os

import azure.functions as func

from shared_code import constants
from shared_code.blob_operations import get_blob_info_from_topic_and_subject, get_blob_client_from_blob_info, get_request_files


def main(msg: func.ServiceBusMessage,
         stepResultEvent: func.Out[func.EventGridOutputEvent],
         toDeleteEvent: func.Out[func.EventGridOutputEvent]):

    logging.info("Python ServiceBus topic trigger processed message - A new blob was created!.")
    body = msg.get_body().decode('utf-8')
    logging.info('Python ServiceBus queue trigger processed message: %s', body)

    json_body = json.loads(body)
    topic = json_body["topic"]
    storage_account_name, request_id, blob_name = get_blob_info_from_topic_and_subject(topic=topic, subject=json_body["subject"])
    request_files = None
    failure_reason = None

    # message originated from in-progress blob creation
    if constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS in topic or constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS in topic:
        try:
            enable_malware_scanning = strtobool(os.environ["ENABLE_MALWARE_SCANNING"])
        except KeyError:
            logging.error("environment variable 'ENABLE_MALWARE_SCANNING' does not exists. Cannot continue.")
            raise

        if enable_malware_scanning:
            # If malware scanning is enabled, the fact that the blob was created can be dismissed.
            # It will be consumed by the malware scanning service
            logging.info('Malware scanning is enabled. no action to perform.')
            return
        else:
            logging.info('Malware scanning is disabled. Completing the submitted stage (moving to in_review).')
            # Malware scanning is disabled, so we skip to the in_review stage
            completed_step = constants.STAGE_SUBMITTED
            new_status = constants.STAGE_IN_REVIEW
            try:
                request_files = get_request_files(account_name=storage_account_name, request_id=request_id)
            except Exception:
                logging.exception("Failed enumerating the files in the request.")
                new_status = constants.STAGE_FAILED
                failure_reason = constants.FAILED_ENUMERATING_REQUEST_FILES_MESSAGE

    # blob created in the approved storage, meaning its ready (success)
    elif constants.STORAGE_ACCOUNT_NAME_IMPORT_APPROVED in topic or constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED in topic:
        completed_step = constants.STAGE_APPROVAL_INPROGRESS
        new_status = constants.STAGE_APPROVED
    # blob created in the rejected storage, meaning its ready (declined)
    elif constants.STORAGE_ACCOUNT_NAME_IMPORT_REJECTED in topic or constants.STORAGE_ACCOUNT_NAME_EXPORT_REJECTED in topic:
        completed_step = constants.STAGE_REJECTION_INPROGRESS
        new_status = constants.STAGE_REJECTED
    # blob created in the blocked storage, meaning its ready (failed)
    elif constants.STORAGE_ACCOUNT_NAME_IMPORT_BLOCKED in topic or constants.STORAGE_ACCOUNT_NAME_EXPORT_BLOCKED in topic:
        completed_step = constants.STAGE_BLOCKING_INPROGRESS
        new_status = constants.STAGE_BLOCKED_BY_SCAN

    # reply with a step completed event
    stepResultEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"completed_step": completed_step, "new_status": new_status, "request_id": request_id, "request_files": request_files, "error_message": failure_reason},
            subject=request_id,
            event_type="Airlock.StepResult",
            event_time=datetime.datetime.utcnow(),
            data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))

    # check blob metadata to find the blob it was copied from
    blob_client = get_blob_client_from_blob_info(storage_account_name=storage_account_name, container_name=request_id, blob_name=blob_name)
    blob_metadata = blob_client.get_blob_properties()["metadata"]
    copied_from = json.loads(blob_metadata["copied_from"])
    logging.info(f"copied from history: {copied_from}")

    # signal that the container where we copied from can now be deleted
    toDeleteEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"blob_to_delete": copied_from[-1]},  # last container in copied_from is the one we just copied from
            subject=request_id,
            event_type="Airlock.ToDelete",
            event_time=datetime.datetime.utcnow(),
            data_version="1.0"
        )
    )
