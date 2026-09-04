import logging
from typing import Optional

import azure.functions as func
import datetime
import os
import uuid
import json

from exceptions import NoFilesInRequestException, TooManyFilesInRequestException, NoDataInRequestException

from shared_code import blob_operations, constants, airlock_storage_helper, parsers
from pydantic import BaseModel, TypeAdapter


class RequestProperties(BaseModel):
    request_id: str
    new_status: str
    previous_status: Optional[str] = None
    type: str
    workspace_id: str
    review_workspace_id: Optional[str] = None
    # Versionless events are pre-v2 and therefore legacy.
    airlock_version: int = 1


class ContainersCopyMetadata:
    source_account_name: str
    dest_account_name: str

    def __init__(self, source_account_name: str, dest_account_name: str):
        self.source_account_name = source_account_name
        self.dest_account_name = dest_account_name


def main(msg: func.ServiceBusMessage, stepResultEvent: func.Out[func.EventGridOutputEvent], dataDeletionEvent: func.Out[func.EventGridOutputEvent]):
    request_properties = None
    request_files = None

    try:
        request_properties = extract_properties(msg)
        request_files = get_request_files(request_properties) if request_properties.new_status == constants.STAGE_SUBMITTED else None
        handle_status_changed(request_properties, stepResultEvent, dataDeletionEvent, request_files)

    except NoFilesInRequestException:
        set_output_event_to_report_failure(stepResultEvent, request_properties, failure_reason=constants.NO_FILES_IN_REQUEST_MESSAGE, request_files=request_files)
    except TooManyFilesInRequestException:
        set_output_event_to_report_failure(stepResultEvent, request_properties, failure_reason=constants.TOO_MANY_FILES_IN_REQUEST_MESSAGE, request_files=request_files)
    except NoDataInRequestException:
        set_output_event_to_report_failure(stepResultEvent, request_properties, failure_reason=constants.NO_DATA_IN_REQUEST_MESSAGE, request_files=request_files)
    except Exception:
        # Only the deterministic validation failures above should fail the request. Anything else may be
        # transient (throttling, identity propagation, DNS, copy polling), so let it escape to be retried
        # by Service Bus and dead-lettered after maxDeliveryCount, rather than silently failing the request.
        logging.exception("Unexpected error processing airlock request; leaving message for Service Bus retry")
        raise


def handle_status_changed(request_properties: RequestProperties, stepResultEvent: func.Out[func.EventGridOutputEvent], dataDeletionEvent: func.Out[func.EventGridOutputEvent], request_files):
    new_status = request_properties.new_status
    previous_status = request_properties.previous_status
    req_id = request_properties.request_id
    ws_id = request_properties.workspace_id
    request_type = request_properties.type

    logging.info('Processing request with id %s. new status is "%s", type is "%s"', req_id, new_status, request_type)

    use_metadata = request_properties.airlock_version >= 2

    if new_status == constants.STAGE_DRAFT:
        if use_metadata:
            from shared_code.blob_operations_metadata import create_container_with_metadata
            account_name = airlock_storage_helper.get_storage_account_name_for_request(request_type, new_status)
            stage = airlock_storage_helper.get_stage_from_status(request_type, new_status)
            draft_container = airlock_storage_helper.get_container_name_for_request(req_id, new_status)
            create_container_with_metadata(account_name, draft_container, stage, workspace_id=ws_id, request_type=request_type)
        else:
            account_name = get_storage_account(status=constants.STAGE_DRAFT, request_type=request_type, short_workspace_id=ws_id)
            blob_operations.create_container(account_name, req_id)
        return

    if new_status == constants.STAGE_CANCELLED:
        if use_metadata:
            storage_account_name = airlock_storage_helper.get_storage_account_name_for_request(request_type, previous_status)
            container_name = airlock_storage_helper.get_container_name_for_request(req_id, previous_status)
        else:
            storage_account_name = get_storage_account(previous_status, request_type, ws_id)
            container_name = req_id
        container_to_delete_url = blob_operations.get_blob_url(account_name=storage_account_name, container_name=container_name)
        set_output_event_to_trigger_container_deletion(dataDeletionEvent, request_properties, container_url=container_to_delete_url)
        return

    if new_status == constants.STAGE_SUBMITTED:
        # v2 submit does not copy, so enforce the single-file rule explicitly.
        if not request_files:
            raise NoFilesInRequestException(constants.NO_FILES_IN_REQUEST_MESSAGE)
        if len(request_files) > 1:
            raise TooManyFilesInRequestException(constants.TOO_MANY_FILES_IN_REQUEST_MESSAGE)

    if (is_require_data_copy(new_status)):
        if use_metadata:
            from shared_code.blob_operations_metadata import update_container_stage, create_container_with_metadata

            source_account = airlock_storage_helper.get_storage_account_name_for_request(request_type, previous_status)
            dest_account = airlock_storage_helper.get_storage_account_name_for_request(request_type, new_status)
            new_stage = airlock_storage_helper.get_stage_from_status(request_type, new_status)

            if source_account == dest_account:
                if new_status == constants.STAGE_SUBMITTED:
                    # Copy out of the draft container and delete it, so any SAS already issued
                    # is revoked structurally rather than by an eventually-consistent condition.
                    draft_container = airlock_storage_helper.get_container_name_for_request(req_id, previous_status)
                    if blob_operations.container_exists(source_account, draft_container):
                        sealed_container_exists = blob_operations.container_exists(dest_account, req_id)
                        if sealed_container_exists and blob_operations.is_submission_sealed(dest_account, req_id):
                            # A prior delivery completed the copy but failed before deleting the draft.
                            # Never overwrite the scanned sealed blob with data from a still-writable draft.
                            logging.info(f'Request {req_id}: sealed copy already complete, deleting the remaining draft')
                        else:
                            failed_copy_deleted = sealed_container_exists and blob_operations.delete_failed_submission_copy(
                                dest_account, req_id)
                            if sealed_container_exists and not failed_copy_deleted and blob_operations.get_request_files(dest_account, req_id):
                                raise RuntimeError(
                                    f'Request {req_id}: refusing to overwrite an incomplete or unmarked sealed submission')
                            logging.info(f'Request {req_id}: Sealing submission - copying {draft_container} to {req_id}')
                            create_container_with_metadata(dest_account, req_id, new_stage, workspace_id=ws_id, request_type=request_type)
                            blob_operations.copy_data(
                                source_account, dest_account, req_id,
                                source_container=draft_container, destination_container=req_id,
                                additional_metadata={blob_operations.SUBMISSION_SEALED_METADATA_KEY: "true"})
                        blob_operations.delete_container(source_account, draft_container)
                    elif blob_operations.container_exists(dest_account, req_id):
                        # A redelivery after the draft was deleted but before the result was published:
                        # the data is already sealed, so resume by re-emitting the completion event.
                        logging.info(f'Request {req_id}: already sealed, re-emitting the submission result')
                    else:
                        raise NoDataInRequestException(f'Request {req_id}: neither the draft nor the sealed container exists, cannot complete submission')

                    try:
                        enable_malware_scanning = parsers.parse_bool(os.environ["ENABLE_MALWARE_SCANNING"])
                    except KeyError:
                        logging.error("environment variable 'ENABLE_MALWARE_SCANNING' does not exist. Cannot continue.")
                        raise
                    if not enable_malware_scanning:
                        logging.info(f'Request {req_id}: Malware scanning disabled, skipping to in_review')
                        stepResultEvent.set(
                            func.EventGridOutputEvent(
                                id=str(uuid.uuid4()),
                                data={"completed_step": constants.STAGE_SUBMITTED, "new_status": constants.STAGE_IN_REVIEW, "request_id": req_id, "request_files": request_files},
                                subject=req_id,
                                event_type="Airlock.StepResult",
                                event_time=datetime.datetime.now(datetime.UTC),
                                data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))
                    else:
                        logging.info(f'Request {req_id}: Malware scanning enabled, scan result gates the move to in_review')
                        set_output_event_to_report_request_files(stepResultEvent, request_properties, request_files)
                    return

                logging.info(f'Request {req_id}: Updating container stage to {new_stage} (no copy needed)')
                update_container_stage(source_account, req_id, new_stage, changed_by='system')

                if new_status in [constants.STAGE_REJECTION_INPROGRESS, constants.STAGE_BLOCKING_INPROGRESS]:
                    final_status = constants.STAGE_REJECTED if new_status == constants.STAGE_REJECTION_INPROGRESS else constants.STAGE_BLOCKED_BY_SCAN
                    logging.info(f'Request {req_id}: Emitting StepResult for terminal transition {new_status} -> {final_status}')
                    stepResultEvent.set(
                        func.EventGridOutputEvent(
                            id=str(uuid.uuid4()),
                            data={"completed_step": new_status, "new_status": final_status, "request_id": req_id},
                            subject=req_id,
                            event_type="Airlock.StepResult",
                            event_time=datetime.datetime.now(datetime.UTC),
                            data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))
            else:
                # BlobCreatedTrigger reports cross-account copy completion.
                logging.info(f'Request {req_id}: Copying from {source_account} to {dest_account}')
                create_container_with_metadata(dest_account, req_id, new_stage, workspace_id=ws_id, request_type=request_type)
                blob_operations.copy_data(source_account, dest_account, req_id)
        else:
            logging.info('Request with id %s. requires data copy between storage accounts', req_id)
            review_ws_id = request_properties.review_workspace_id
            containers_metadata = get_source_dest_for_copy(new_status=new_status, previous_status=previous_status, request_type=request_type, short_workspace_id=ws_id, review_workspace_id=review_ws_id)
            blob_operations.create_container(containers_metadata.dest_account_name, req_id)
            blob_operations.copy_data(containers_metadata.source_account_name,
                                      containers_metadata.dest_account_name, req_id)
            if new_status == constants.STAGE_SUBMITTED:
                set_output_event_to_report_request_files(stepResultEvent, request_properties, request_files)
        return

    # Other statuses which do not require data copy are dismissed as we don't need to do anything...


def extract_properties(msg: func.ServiceBusMessage) -> RequestProperties:
    try:
        body = msg.get_body().decode('utf-8')
        logging.debug('Python ServiceBus queue trigger processed message: %s', body)
        json_body = json.loads(body)
        result = TypeAdapter(RequestProperties).validate_python(json_body["data"])
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


def get_source_dest_for_copy(new_status: str, previous_status: str, request_type: str, short_workspace_id: str, review_workspace_id: str = None) -> ContainersCopyMetadata:
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
    dest_account_name = get_storage_account_destination_for_copy(new_status, request_type, short_workspace_id, review_workspace_id=review_workspace_id)
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


def get_storage_account_destination_for_copy(new_status: str, request_type: str, short_workspace_id: str, review_workspace_id: str = None) -> str:
    tre_id = _get_tre_id()

    if request_type == constants.IMPORT_TYPE:
        if new_status == constants.STAGE_SUBMITTED:
            # review_workspace_id must not affect the v1 account.
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
    if request_properties is None:
        logging.exception(
            "Failed processing Airlock request: unable to extract request properties. Failure reason: %s",
            failure_reason,
        )
        raise

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
    use_metadata = request_properties.airlock_version >= 2
    container_name = None
    if use_metadata:
        storage_account_name = airlock_storage_helper.get_storage_account_name_for_request(request_properties.type, request_properties.previous_status)
        container_name = airlock_storage_helper.get_container_name_for_request(request_properties.request_id, request_properties.previous_status)
        # On a redelivery the draft is already sealed away, so enumerate the submitted copy instead.
        if not blob_operations.container_exists(storage_account_name, container_name):
            container_name = request_properties.request_id
            # Neither container present means there is no data to submit; fail cleanly rather than
            # letting a ResourceNotFoundError escape to Service Bus retry/dead-letter (stuck in Submitted).
            if not blob_operations.container_exists(storage_account_name, container_name):
                raise NoDataInRequestException(f'Request {request_properties.request_id}: neither the draft nor the sealed container exists, cannot enumerate request files')
    else:
        storage_account_name = get_storage_account(request_properties.previous_status, request_properties.type, request_properties.workspace_id)
    return blob_operations.get_request_files(account_name=storage_account_name, request_id=request_properties.request_id, container_name=container_name)


def _get_tre_id():
    try:
        tre_id = os.environ["TRE_ID"]
    except KeyError as e:
        logging.error(f'Missing environment variable: {e}')
        raise
    return tre_id
