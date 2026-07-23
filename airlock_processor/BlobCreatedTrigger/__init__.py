import logging
import datetime
import uuid
import json
import re
import os

import azure.functions as func

from shared_code import constants, parsers
from shared_code.blob_operations import get_blob_info_from_topic_and_subject, get_blob_client_from_blob_info


# Mapping from v2 container metadata stage to (completed_step, new_status)
V2_STAGE_COMPLETION_MAP = {
    constants.STAGE_IMPORT_APPROVED: (constants.STAGE_APPROVAL_INPROGRESS, constants.STAGE_APPROVED),
    constants.STAGE_IMPORT_REJECTED: (constants.STAGE_REJECTION_INPROGRESS, constants.STAGE_REJECTED),
    constants.STAGE_IMPORT_BLOCKED: (constants.STAGE_BLOCKING_INPROGRESS, constants.STAGE_BLOCKED_BY_SCAN),
    constants.STAGE_EXPORT_APPROVED: (constants.STAGE_APPROVAL_INPROGRESS, constants.STAGE_APPROVED),
    constants.STAGE_EXPORT_REJECTED: (constants.STAGE_REJECTION_INPROGRESS, constants.STAGE_REJECTED),
    constants.STAGE_EXPORT_BLOCKED: (constants.STAGE_BLOCKING_INPROGRESS, constants.STAGE_BLOCKED_BY_SCAN),
}


def main(msg: func.ServiceBusMessage,
         stepResultEvent: func.Out[func.EventGridOutputEvent],
         dataDeletionEvent: func.Out[func.EventGridOutputEvent]):

    logging.info("Python ServiceBus topic trigger processed message - A new blob was created!.")
    body = msg.get_body().decode('utf-8')
    logging.info('Python ServiceBus queue trigger processed message: %s', body)

    json_body = json.loads(body)
    topic = json_body["topic"]
    request_id = re.search(r'/blobServices/default/containers/(.*?)/blobs', json_body["subject"]).group(1)

    # Check if this event is from a v2 consolidated storage account
    if constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE in topic or constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL in topic:
        _handle_v2_blob_created(json_body, topic, request_id, stepResultEvent, dataDeletionEvent)
        return

    # Legacy v1 handling below
    # message originated from in-progress blob creation
    if constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS in topic or constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS in topic:
        try:
            enable_malware_scanning = parsers.parse_bool(os.environ["ENABLE_MALWARE_SCANNING"])
        except KeyError:
            logging.error("environment variable 'ENABLE_MALWARE_SCANNING' does not exists. Cannot continue.")
            raise

        if enable_malware_scanning and (constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS in topic or constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS in topic):
            # If malware scanning is enabled, the fact that the blob was created can be dismissed.
            # It will be consumed by the malware scanning service
            logging.info('Malware scanning is enabled. no action to perform.')
            send_delete_event(dataDeletionEvent, json_body, request_id)
            return
        else:
            logging.info('Malware scanning is disabled. Completing the submitted stage (moving to in_review).')
            # Malware scanning is disabled, so we skip to the in_review stage
            completed_step = constants.STAGE_SUBMITTED
            new_status = constants.STAGE_IN_REVIEW

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
    else:
        logging.warning(f"Unknown storage account in topic: {topic}")
        return

    # reply with a step completed event
    stepResultEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"completed_step": completed_step, "new_status": new_status, "request_id": request_id},
            subject=request_id,
            event_type="Airlock.StepResult",
            event_time=datetime.datetime.now(datetime.UTC),
            data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))

    send_delete_event(dataDeletionEvent, json_body, request_id)


def send_delete_event(dataDeletionEvent: func.Out[func.EventGridOutputEvent], json_body, request_id):
    # check blob metadata to find the blob it was copied from
    blob_client = get_blob_client_from_blob_info(
        *get_blob_info_from_topic_and_subject(topic=json_body["topic"], subject=json_body["subject"]))
    blob_metadata = blob_client.get_blob_properties()["metadata"]
    copied_from = json.loads(blob_metadata["copied_from"])
    logging.info(f"copied from history: {copied_from}")

    # signal that the container where we copied from can now be deleted
    dataDeletionEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"blob_to_delete": copied_from[-1]},  # last container in copied_from is the one we just copied from
            subject=request_id,
            event_type="Airlock.DataDeletion",
            event_time=datetime.datetime.now(datetime.UTC),
            data_version=constants.DATA_DELETION_EVENT_DATA_VERSION
        )
    )


def _handle_v2_blob_created(json_body, topic, request_id, stepResultEvent, dataDeletionEvent):
    """Handle BlobCreated events from v2 consolidated storage accounts.

    In v2, cross-account copies (e.g., import approval: core → workspace-global)
    fire BlobCreated events. Container metadata determines the stage and appropriate
    step result, matching the v1 pattern where BlobCreatedTrigger signals copy completion.
    """
    storage_account_name, _, _ = get_blob_info_from_topic_and_subject(
        topic=json_body["topic"], subject=json_body["subject"])

    from shared_code.blob_operations_metadata import get_container_metadata
    try:
        metadata = get_container_metadata(storage_account_name, request_id)
    except Exception:
        logging.warning(f"Could not read container metadata for request {request_id} on {storage_account_name}, skipping")
        return

    stage = metadata.get('stage', '')
    logging.info(f"V2 BlobCreated for request {request_id}: stage={stage}, account={storage_account_name}")

    if stage in V2_STAGE_COMPLETION_MAP:
        completed_step, new_status = V2_STAGE_COMPLETION_MAP[stage]
        logging.info(f"V2 copy completed for request {request_id}: {completed_step} -> {new_status}")

        stepResultEvent.set(
            func.EventGridOutputEvent(
                id=str(uuid.uuid4()),
                data={"completed_step": completed_step, "new_status": new_status, "request_id": request_id},
                subject=request_id,
                event_type="Airlock.StepResult",
                event_time=datetime.datetime.now(datetime.UTC),
                data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))

        # Send delete event for the source container (same as v1)
        send_delete_event(dataDeletionEvent, json_body, request_id)
    else:
        # Non-terminal stages (e.g., import-external from user upload, export-internal)
        # are not copy completions — ignore them
        logging.info(f"V2 BlobCreated for non-terminal stage '{stage}' on request {request_id}, no action needed")
