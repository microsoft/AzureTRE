import os
from shared_code import constants


def get_container_name_for_request(request_id: str, status: str) -> str:
    if status == constants.STAGE_DRAFT:
        return f"{request_id}{constants.DRAFT_CONTAINER_SUFFIX}"
    return request_id


def get_request_id_from_container_name(container_name: str) -> str:
    if container_name.endswith(constants.DRAFT_CONTAINER_SUFFIX):
        return container_name[:-len(constants.DRAFT_CONTAINER_SUFFIX)]
    return container_name


def get_storage_account_name_for_request(request_type: str, status: str) -> str:
    # v1 routing lives in StatusChangedQueueTrigger.get_storage_account.
    tre_id = os.environ.get("TRE_ID", "")

    if request_type == constants.IMPORT_TYPE:
        if status in [constants.STAGE_DRAFT, constants.STAGE_SUBMITTED, constants.STAGE_IN_REVIEW,
                      constants.STAGE_REJECTED, constants.STAGE_REJECTION_INPROGRESS,
                      constants.STAGE_BLOCKED_BY_SCAN, constants.STAGE_BLOCKING_INPROGRESS]:
            return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE + tre_id
        return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL + tre_id

    if status in [constants.STAGE_APPROVED, constants.STAGE_APPROVAL_INPROGRESS]:
        return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE + tre_id
    return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL + tre_id


def get_stage_from_status(request_type: str, status: str) -> str:
    if request_type == constants.IMPORT_TYPE:
        if status == constants.STAGE_DRAFT:
            return constants.STAGE_IMPORT_EXTERNAL
        elif status in [constants.STAGE_SUBMITTED, constants.STAGE_IN_REVIEW]:
            return constants.STAGE_IMPORT_IN_PROGRESS
        elif status in [constants.STAGE_APPROVED, constants.STAGE_APPROVAL_INPROGRESS]:
            return constants.STAGE_IMPORT_APPROVED
        elif status in [constants.STAGE_REJECTED, constants.STAGE_REJECTION_INPROGRESS]:
            return constants.STAGE_IMPORT_REJECTED
        elif status in [constants.STAGE_BLOCKED_BY_SCAN, constants.STAGE_BLOCKING_INPROGRESS]:
            return constants.STAGE_IMPORT_BLOCKED
    else:
        if status == constants.STAGE_DRAFT:
            return constants.STAGE_EXPORT_INTERNAL
        elif status in [constants.STAGE_SUBMITTED, constants.STAGE_IN_REVIEW]:
            return constants.STAGE_EXPORT_IN_PROGRESS
        elif status in [constants.STAGE_APPROVED, constants.STAGE_APPROVAL_INPROGRESS]:
            return constants.STAGE_EXPORT_APPROVED
        elif status in [constants.STAGE_REJECTED, constants.STAGE_REJECTION_INPROGRESS]:
            return constants.STAGE_EXPORT_REJECTED
        elif status in [constants.STAGE_BLOCKED_BY_SCAN, constants.STAGE_BLOCKING_INPROGRESS]:
            return constants.STAGE_EXPORT_BLOCKED

    return "unknown"
