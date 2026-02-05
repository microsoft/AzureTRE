import logging
import datetime
import uuid
import json
import re
import os

import azure.functions as func

from shared_code import constants, parsers
from shared_code.blob_operations import get_blob_info_from_topic_and_subject, get_blob_client_from_blob_info


def main(msg: func.ServiceBusMessage,
         stepResultEvent: func.Out[func.EventGridOutputEvent],
         dataDeletionEvent: func.Out[func.EventGridOutputEvent]):

    logging.info("Python ServiceBus topic trigger processed message - A new blob was created!.")
    body = msg.get_body().decode('utf-8')
    logging.info('Python ServiceBus queue trigger processed message: %s', body)

    json_body = json.loads(body)
    topic = json_body["topic"]
    request_id = re.search(r'/blobServices/default/containers/(.*?)/blobs', json_body["subject"]).group(1)

    # Check if we're using consolidated storage accounts (metadata-based approach)
    use_metadata_routing = os.getenv('USE_METADATA_STAGE_MANAGEMENT', 'false').lower() == 'true'
    
    if use_metadata_routing:
        # NEW: Determine if this is from external/approved (public) or consolidated (private with metadata)
        if constants.STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL in topic:
            # Import external (draft) - no processing needed, wait for submit
            logging.info('Blob created in import external storage. No action needed.')
            return
        elif constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED in topic:
            # Export approved - finalize as approved
            completed_step = constants.STAGE_APPROVAL_INPROGRESS
            new_status = constants.STAGE_APPROVED
        else:
            # Consolidated storage - get stage from container metadata
            from shared_code.blob_operations_metadata import get_container_metadata
            storage_account_name = parse_storage_account_name_from_topic(topic)
            metadata = get_container_metadata(storage_account_name, request_id)
            stage = metadata.get('stage', 'unknown')
            
            # Route based on metadata stage
            if stage in ['import-in-progress', 'export-in-progress']:
                handle_inprogress_stage(stage, request_id, dataDeletionEvent, json_body, stepResultEvent)
                return
            elif stage in ['import-approved', 'export-approved']:
                # Shouldn't happen - approved goes to separate accounts now
                logging.warning(f"Unexpected approved stage in consolidated storage: {stage}")
                return
            elif stage in ['import-rejected', 'export-rejected']:
                completed_step = constants.STAGE_REJECTION_INPROGRESS
                new_status = constants.STAGE_REJECTED
            elif stage in ['import-blocked', 'export-blocked']:
                completed_step = constants.STAGE_BLOCKING_INPROGRESS
                new_status = constants.STAGE_BLOCKED_BY_SCAN
            else:
                logging.warning(f"Unknown stage in container metadata: {stage}")
                return
    else:
        # LEGACY: Determine stage from storage account name in topic
        if constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS in topic or constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS in topic:
            handle_inprogress_stage_legacy(topic, request_id, dataDeletionEvent, json_body, stepResultEvent)
            return
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


def parse_storage_account_name_from_topic(topic: str) -> str:
    """Extract storage account name from EventGrid topic."""
    # Topic format: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{account}
    match = re.search(r'/storageAccounts/([^/]+)', topic)
    if match:
        return match.group(1)
    raise ValueError(f"Could not parse storage account name from topic: {topic}")


def handle_inprogress_stage(stage: str, request_id: str, dataDeletionEvent, json_body, stepResultEvent):
    """Handle in-progress stages with metadata-based routing."""
    try:
        enable_malware_scanning = parsers.parse_bool(os.environ["ENABLE_MALWARE_SCANNING"])
    except KeyError:
        logging.error("environment variable 'ENABLE_MALWARE_SCANNING' does not exists. Cannot continue.")
        raise

    if enable_malware_scanning:
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
        
        stepResultEvent.set(
            func.EventGridOutputEvent(
                id=str(uuid.uuid4()),
                data={"completed_step": completed_step, "new_status": new_status, "request_id": request_id},
                subject=request_id,
                event_type="Airlock.StepResult",
                event_time=datetime.datetime.now(datetime.UTC),
                data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))
        
        send_delete_event(dataDeletionEvent, json_body, request_id)


def handle_inprogress_stage_legacy(topic: str, request_id: str, dataDeletionEvent, json_body, stepResultEvent):
    """Handle in-progress stages with legacy storage account-based routing."""
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
