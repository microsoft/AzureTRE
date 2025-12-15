import logging
from typing import Optional

import azure.functions as func
import datetime
import os
import uuid
import json

from exceptions import NoFilesInRequestException, TooManyFilesInRequestException

from shared_code import blob_operations, constants
from pydantic import BaseModel, parse_obj_as


class RequestProperties(BaseModel):
    request_id: str
    new_status: str
    previous_status: Optional[str]
    type: str
    workspace_id: str


class ContainersCopyMetadata:
    source_account_name: str
    dest_account_name: str

    def __init__(self, source_account_name: str, dest_account_name: str):
        self.source_account_name = source_account_name
        self.dest_account_name = dest_account_name


def main(msg: func.ServiceBusMessage, stepResultEvent: func.Out[func.EventGridOutputEvent], dataDeletionEvent: func.Out[func.EventGridOutputEvent]):
    try:
        request_properties = extract_properties(msg)
        request_files = get_request_files(request_properties) if request_properties.new_status == constants.STAGE_SUBMITTED else None
        handle_status_changed(request_properties, stepResultEvent, dataDeletionEvent, request_files)

    except NoFilesInRequestException:
        set_output_event_to_report_failure(stepResultEvent, request_properties, failure_reason=constants.NO_FILES_IN_REQUEST_MESSAGE, request_files=request_files)
    except TooManyFilesInRequestException:
        set_output_event_to_report_failure(stepResultEvent, request_properties, failure_reason=constants.TOO_MANY_FILES_IN_REQUEST_MESSAGE, request_files=request_files)
    except Exception:
        set_output_event_to_report_failure(stepResultEvent, request_properties, failure_reason=constants.UNKNOWN_REASON_MESSAGE, request_files=request_files)


def handle_status_changed(request_properties: RequestProperties, stepResultEvent: func.Out[func.EventGridOutputEvent], dataDeletionEvent: func.Out[func.EventGridOutputEvent], request_files):
    new_status = request_properties.new_status
    previous_status = request_properties.previous_status
    req_id = request_properties.request_id
    ws_id = request_properties.workspace_id
    request_type = request_properties.type

    logging.info('Processing request with id %s. new status is "%s", type is "%s"', req_id, new_status, request_type)

    if new_status == constants.STAGE_DRAFT:
        account_name = get_storage_account(status=constants.STAGE_DRAFT, request_type=request_type, short_workspace_id=ws_id)
        blob_operations.create_container(account_name, req_id)
        return

    if new_status == constants.STAGE_CANCELLED:
        storage_account_name = get_storage_account(previous_status, request_type, ws_id)
        container_to_delete_url = blob_operations.get_blob_url(account_name=storage_account_name, container_name=req_id)
        set_output_event_to_trigger_container_deletion(dataDeletionEvent, request_properties, container_url=container_to_delete_url)
        return

    if new_status == constants.STAGE_SUBMITTED:
        set_output_event_to_report_request_files(stepResultEvent, request_properties, request_files)

    if (is_require_data_copy(new_status)):
        logging.info('Request with id %s. requires data copy between storage accounts', req_id)
        containers_metadata = get_source_dest_for_copy(new_status=new_status, previous_status=previous_status, request_type=request_type, short_workspace_id=ws_id)
        blob_operations.create_container(containers_metadata.dest_account_name, req_id)
        blob_operations.copy_data(containers_metadata.source_account_name,
                                  containers_metadata.dest_account_name, req_id)
        return

    # Other statuses which do not require data copy are dismissed as we don't need to do anything...


def extract_properties(msg: func.ServiceBusMessage) -> RequestProperties:
    try:
        body = msg.get_body().decode('utf-8')
        logging.debug('Python ServiceBus queue trigger processed message: %s', body)
        json_body = json.loads(body)
        result = parse_obj_as(RequestProperties, json_body["data"])
        if not result:
            raise Exception("Failed parsing request properties")
    except json.decoder.JSONDecodeError:
        logging.error(f'Error decoding object: {body}')
        raise
    except Exception as e:
        logging.error(f'Error extracting properties: {e}')
        raise

    return result


def is_require_data_copy(new_status: str):
    if new_status.lower() in [constants.STAGE_SUBMITTED, constants.STAGE_APPROVAL_INPROGRESS, constants.STAGE_REJECTION_INPROGRESS, constants.STAGE_BLOCKING_INPROGRESS]:
        return True
    return False


def get_source_dest_for_copy(new_status: str, previous_status: str, request_type: str, short_workspace_id: str) -> ContainersCopyMetadata:
    # sanity
    if is_require_data_copy(new_status) is False:
        raise Exception("Given new status is not supported")

    request_type = request_type.lower()
    if request_type != constants.IMPORT_TYPE and request_type != constants.EXPORT_TYPE:
        msg = "Airlock request type must be either '{}' or '{}".format(str(constants.IMPORT_TYPE),
                                                                       str(constants.EXPORT_TYPE))
        logging.error(msg)
        raise Exception(msg)

    source_account_name = get_storage_account(previous_status, request_type, short_workspace_id)
    dest_account_name = get_storage_account_destination_for_copy(new_status, request_type, short_workspace_id)
    return ContainersCopyMetadata(source_account_name, dest_account_name)


def get_storage_account(status: str, request_type: str, short_workspace_id: str) -> str:
    tre_id = _get_tre_id()

    if request_type == constants.IMPORT_TYPE:
        if status == constants.STAGE_DRAFT:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL + tre_id
        elif status == constants.STAGE_APPROVED:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_APPROVED + short_workspace_id
        elif status == constants.STAGE_REJECTED:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_REJECTED + tre_id
        elif status == constants.STAGE_BLOCKED_BY_SCAN:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_BLOCKED + tre_id
        elif status in [constants.STAGE_IN_REVIEW, constants.STAGE_SUBMITTED, constants.STAGE_APPROVAL_INPROGRESS, constants.STAGE_REJECTION_INPROGRESS, constants.STAGE_BLOCKING_INPROGRESS]:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS + tre_id

    if request_type == constants.EXPORT_TYPE:
        if status == constants.STAGE_DRAFT:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL + short_workspace_id
        elif status == constants.STAGE_APPROVED:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED + tre_id
        elif status == constants.STAGE_REJECTED:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_REJECTED + short_workspace_id
        elif status == constants.STAGE_BLOCKED_BY_SCAN:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_BLOCKED + short_workspace_id
        elif status in [constants.STAGE_IN_REVIEW, constants.STAGE_SUBMITTED, constants.STAGE_APPROVAL_INPROGRESS, constants.STAGE_REJECTION_INPROGRESS, constants.STAGE_BLOCKING_INPROGRESS]:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS + short_workspace_id

    error_message = f"Missing current storage account definition for status '{status}' and request type '{request_type}'."
    logging.error(error_message)
    raise Exception(error_message)


def get_storage_account_destination_for_copy(new_status: str, request_type: str, short_workspace_id: str) -> str:
    tre_id = _get_tre_id()

    if request_type == constants.IMPORT_TYPE:
        if new_status == constants.STAGE_SUBMITTED:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS + tre_id
        elif new_status == constants.STAGE_APPROVAL_INPROGRESS:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_APPROVED + short_workspace_id
        elif new_status == constants.STAGE_REJECTION_INPROGRESS:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_REJECTED + tre_id
        elif new_status == constants.STAGE_BLOCKING_INPROGRESS:
            return constants.STORAGE_ACCOUNT_NAME_IMPORT_BLOCKED + tre_id

    if request_type == constants.EXPORT_TYPE:
        if new_status == constants.STAGE_SUBMITTED:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS + short_workspace_id
        elif new_status == constants.STAGE_APPROVAL_INPROGRESS:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED + tre_id
        elif new_status == constants.STAGE_REJECTION_INPROGRESS:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_REJECTED + short_workspace_id
        elif new_status == constants.STAGE_BLOCKING_INPROGRESS:
            return constants.STORAGE_ACCOUNT_NAME_EXPORT_BLOCKED + short_workspace_id

    error_message = f"Missing copy destination storage account definition for status '{new_status}' and request type '{request_type}'."
    logging.error(error_message)
    raise Exception(error_message)


def set_output_event_to_report_failure(stepResultEvent, request_properties, failure_reason, request_files):
    logging.exception(f"Failed processing Airlock request with ID: '{request_properties.request_id}', changing request status to '{constants.STAGE_FAILED}'.")
    stepResultEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"completed_step": request_properties.new_status, "new_status": constants.STAGE_FAILED, "request_id": request_properties.request_id, "request_files": request_files, "status_message": failure_reason},
            subject=request_properties.request_id,
            event_type="Airlock.StepResult",
            event_time=datetime.datetime.now(datetime.UTC),
            data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))


def set_output_event_to_report_request_files(stepResultEvent, request_properties, request_files):
    logging.info(f'Sending file enumeration result for request with ID: {request_properties.request_id} result: {request_files}')
    stepResultEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"completed_step": request_properties.new_status, "request_id": request_properties.request_id, "request_files": request_files},
            subject=request_properties.request_id,
            event_type="Airlock.StepResult",
            event_time=datetime.datetime.now(datetime.UTC),
            data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))


def set_output_event_to_trigger_container_deletion(dataDeletionEvent, request_properties, container_url):
    logging.info(f'Sending container deletion event for request ID: {request_properties.request_id}. container URL: {container_url}')
    dataDeletionEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"blob_to_delete": container_url},
            subject=request_properties.request_id,
            event_type="Airlock.DataDeletion",
            event_time=datetime.datetime.now(datetime.UTC),
            data_version=constants.DATA_DELETION_EVENT_DATA_VERSION
        )
    )


def get_request_files(request_properties: RequestProperties):
    storage_account_name = get_storage_account(request_properties.previous_status, request_properties.type, request_properties.workspace_id)
    return blob_operations.get_request_files(account_name=storage_account_name, request_id=request_properties.request_id)


def _get_tre_id():
    try:
        tre_id = os.environ["TRE_ID"]
    except KeyError as e:
        logging.error(f'Missing environment variable: {e}')
        raise
    return tre_id
