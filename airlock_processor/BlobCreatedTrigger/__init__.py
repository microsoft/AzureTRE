from distutils.util import strtobool
from shared_code import constants, storage_accounts
import logging

import azure.functions as func
import datetime
import uuid
import json
import re
import os


def main(msg: func.ServiceBusMessage,
         stepResultEvent: func.Out[func.EventGridOutputEvent],
         toDeleteEvent: func.Out[func.EventGridOutputEvent]):

    logging.info("Python ServiceBus topic trigger processed message - A new blob was created!.")
    body = msg.get_body().decode('utf-8')
    logging.info('Python ServiceBus queue trigger processed message: %s', body)

    json_body = json.loads(body)

    # Example of a topic: "/subscriptions/<subscription_id>/resourceGroups/rg-tanyaair1/providers/Microsoft.Storage/storageAccounts/stalimiptanyaair1"
    topic = json_body["topic"]
    request_id = re.search(r'/blobServices/default/containers/(.*?)/blobs', json_body["subject"]).group(1)

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

    if constants.STORAGE_ACCOUNT_NAME_EXPORT_PREFIX in topic:
        request_type = constants.IMPORT_TYPE
    elif constants.STORAGE_ACCOUNT_NAME_IMPORT_PREFIX in topic:
        request_type = constants.EXPORT_TYPE
    else:
        logging.error(f"Can't determine type of request from topic {topic}")
        raise

    src = storage_accounts.source_storage_account_from_dest(
        request_type=request_type,
        # TODO: other arguments?????
    )

    toDeleteEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={},  # TODO(tanya): what information do we need? # request_id, account_name, account_rg
            subject=request_id,
            event_type="Airlock.ToDelete",
            event_time=datetime.datetime.utcnow(),
            data_version="1.0"
        )
    )

    # reply with a step completed event
    stepResultEvent.set(
        func.EventGridOutputEvent(
            id=str(uuid.uuid4()),
            data={"completed_step": completed_step, "new_status": new_status, "request_id": request_id},
            subject=request_id,
            event_type="Airlock.StepResult",
            event_time=datetime.datetime.utcnow(),
            data_version=constants.STEP_RESULT_EVENT_DATA_VERSION))
