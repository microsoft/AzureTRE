import logging

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
    status: str
    type: str
    workspace_id: str


class ContainersCopyMetadata:
    source_account_name: str
    dest_account_name: str

    def __init__(self, source_account_name: str, dest_account_name: str):
        self.source_account_name = source_account_name
        self.dest_account_name = dest_account_name


def main(msg: func.ServiceBusMessage, outputEvent: func.Out[func.EventGridOutputEvent]):
    try:
        request_properties = extract_properties(msg)
        request_files = get_request_files(request_properties) if request_properties.status == constants.STAGE_SUBMITTED else None
        handle_status_changed(request_properties, outputEvent, request_files)

    except NoFilesInRequestException:
        set_output_event_to_report_failure(outputEvent, request_properties, failure_reason=constants.NO_FILES_IN_REQUEST_MESSAGE, request_files=request_files)
    except TooManyFilesInRequestException:
        set_output_event_to_report_failure(outputEvent, request_properties, failure_reason=constants.TOO_MANY_FILES_IN_REQUEST_MESSAGE, request_files=request_files)
    except Exception:
        set_output_event_to_report_failure(outputEvent, request_properties, failure_reason=constants.UNKNOWN_REASON_MESSAGE, request_files=request_files)


def handle_status_changed(request_properties: RequestProperties, outputEvent: func.Out[func.EventGridOutputEvent], request_files):
    new_status = request_properties.status
    req_id = request_properties.request_id
    ws_id = request_properties.workspace_id
    request_type = request_properties.type

    logging.info('Processing request with id %s. new status is "%s", type is "%s"', req_id, new_status, request_type)

    try:
        tre_id = os.environ["TRE_ID"]
    except KeyError as e:
        logging.error(f'Missing environment variable: {e}')
        raise

    if new_status == constants.STAGE_DRAFT and request_type == constants.IMPORT_TYPE:
        account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL + tre_id
        blob_operations.create_container(account_name, req_id)
        return

    if new_status == constants.STAGE_DRAFT and request_type == constants.EXPORT_TYPE:
        account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL + ws_id
        blob_operations.create_container(account_name, req_id)
        return

    if new_status == constants.STAGE_SUBMITTED:
        set_output_event_to_report_request_files(outputEvent, request_properties, request_files)

    if (is_require_data_copy(new_status)):
        logging.info('Request with id %s. requires data copy between storage accounts', req_id)
        containers_metadata = get_source_dest_for_copy(new_status, request_type, ws_id)
        blob_operations.create_container(containers_metadata.dest_account_name, req_id)
        blob_operations.copy_data(containers_metadata.source_account_name,
                                  containers_metadata.dest_account_name, req_id)
        return

    # Other statuses which do not require data copy are dismissed as we don't need to do anything...


def extract_properties(msg: func.ServiceBusMessage) -> RequestProperties:
    try:
        body = msg.get_body().decode('utf-8')
        logging.info('Python ServiceBus queue trigger processed message: %s', body)
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


def get_source_dest_for_copy(new_status: str, request_type: str, short_workspace_id: str) -> ContainersCopyMetadata:
    # sanity
    if is_require_data_copy(new_status) is False:
        raise Exception("Given new status is not supported")

    try:
        tre_id = os.environ["TRE_ID"]
    except KeyError as e:
        logging.error(f'Missing environment variable: {e}')
        raise

    request_type = request_type.lower()
    if request_type != constants.IMPORT_TYPE and request_type != constants.EXPORT_TYPE:
        msg = "Airlock request type must be either '{}' or '{}".format(str(constants.IMPORT_TYPE),
                                                                       str(constants.EXPORT_TYPE))
        logging.error(msg)
        raise Exception(msg)

    if request_type == constants.IMPORT_TYPE:
        if new_status == constants.STAGE_SUBMITTED:
            source_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL + tre_id
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS + tre_id
        elif new_status == constants.STAGE_APPROVAL_INPROGRESS:
            source_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS + tre_id
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_APPROVED + short_workspace_id
        elif new_status == constants.STAGE_REJECTION_INPROGRESS:
            source_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS + tre_id
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_REJECTED + tre_id
        elif new_status == constants.STAGE_BLOCKING_INPROGRESS:
            source_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS + tre_id
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_IMPORT_BLOCKED + tre_id
    else:
        if new_status == constants.STAGE_SUBMITTED:
            source_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL + short_workspace_id
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS + short_workspace_id
        elif new_status == constants.STAGE_APPROVAL_INPROGRESS:
            source_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS + short_workspace_id
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED + tre_id
        elif new_status == constants.STAGE_REJECTION_INPROGRESS:
            source_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS + short_workspace_id
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_REJECTED + short_workspace_id
        elif new_status == constants.STAGE_BLOCKING_INPROGRESS:
            source_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS + short_workspace_id
            dest_account_name = constants.STORAGE_ACCOUNT_NAME_EXPORT_BLOCKED + short_workspace_id

    return ContainersCopyMetadata(source_account_name, dest_account_name)


def set_output_event_to_report_failure(outputEvent, request_properties, failure_reason, request_files):
    logging.exception(f"Failed processing Airlock request with ID: '{request_properties.request_id}', changing request status to '{constants.STAGE_FAILED}'.")
    outputEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"completed_step": request_properties.status, "new_status": constants.STAGE_FAILED, "request_id": request_properties.request_id, "request_files": request_files, "error_message": failure_reason},
            subject=request_properties.request_id,
            event_type="Airlock.StepResult",
            event_time=datetime.datetime.utcnow(),
            data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))


def set_output_event_to_report_request_files(outputEvent, request_properties, request_files):
    outputEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"completed_step": request_properties.status, "request_id": request_properties.request_id, "request_files": request_files},
            subject=request_properties.request_id,
            event_type="Airlock.StepResult",
            event_time=datetime.datetime.utcnow(),
            data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))


def get_request_files(request_properties):
    containers_metadata = get_source_dest_for_copy(request_properties.status, request_properties.type, request_properties.workspace_id)
    storage_account_name = containers_metadata.source_account_name
    return blob_operations.get_request_files(account_name=storage_account_name, request_id=request_properties.request_id)
