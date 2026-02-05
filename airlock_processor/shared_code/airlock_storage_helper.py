import os
from shared_code import constants


def use_metadata_stage_management() -> bool:
    return os.getenv('USE_METADATA_STAGE_MANAGEMENT', 'false').lower() == 'true'


def get_storage_account_name_for_request(request_type: str, status: str, short_workspace_id: str) -> str:
    tre_id = os.environ.get("TRE_ID", "")
    
    if use_metadata_stage_management():
        # Global workspace storage - all workspaces use same account
        if request_type == constants.IMPORT_TYPE:
            if status in [constants.STAGE_DRAFT, constants.STAGE_SUBMITTED, constants.STAGE_IN_REVIEW, 
                         constants.STAGE_REJECTED, constants.STAGE_REJECTION_INPROGRESS,
                         constants.STAGE_BLOCKED_BY_SCAN, constants.STAGE_BLOCKING_INPROGRESS]:
                # ALL core import stages in stalairlock
                return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE + tre_id
            else:  # Approved, approval in progress
                # Global workspace storage
                return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL + tre_id
        else:  # export
            if status in [constants.STAGE_APPROVED, constants.STAGE_APPROVAL_INPROGRESS]:
                # Export approved in core
                return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE + tre_id
            else:  # Draft, submitted, in-review, rejected, blocked
                # Global workspace storage
                return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL + tre_id
    else:
        # Legacy mode
        if request_type == constants.IMPORT_TYPE:
            if status == constants.STAGE_DRAFT:
                return constants.STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL + tre_id
            elif status in [constants.STAGE_SUBMITTED, constants.STAGE_IN_REVIEW, constants.STAGE_APPROVAL_INPROGRESS, 
                           constants.STAGE_REJECTION_INPROGRESS, constants.STAGE_BLOCKING_INPROGRESS]:
                return constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS + tre_id
            elif status == constants.STAGE_APPROVED:
                return constants.STORAGE_ACCOUNT_NAME_IMPORT_APPROVED + short_workspace_id
            elif status == constants.STAGE_REJECTED:
                return constants.STORAGE_ACCOUNT_NAME_IMPORT_REJECTED + tre_id
            elif status == constants.STAGE_BLOCKED_BY_SCAN:
                return constants.STORAGE_ACCOUNT_NAME_IMPORT_BLOCKED + tre_id
        else:  # export
            if status == constants.STAGE_DRAFT:
                return constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL + short_workspace_id
            elif status in [constants.STAGE_SUBMITTED, constants.STAGE_IN_REVIEW, constants.STAGE_APPROVAL_INPROGRESS,
                           constants.STAGE_REJECTION_INPROGRESS, constants.STAGE_BLOCKING_INPROGRESS]:
                return constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS + short_workspace_id
            elif status == constants.STAGE_APPROVED:
                return constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED + tre_id
            elif status == constants.STAGE_REJECTED:
                return constants.STORAGE_ACCOUNT_NAME_EXPORT_REJECTED + short_workspace_id
            elif status == constants.STAGE_BLOCKED_BY_SCAN:
                return constants.STORAGE_ACCOUNT_NAME_EXPORT_BLOCKED + short_workspace_id


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
    else:  # export
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
