from typing import Tuple
from core import config
from models.domain.airlock_request import AirlockRequestStatus
from models.domain.workspace import Workspace
from resources import constants


def use_metadata_stage_management() -> bool:
    return config.USE_METADATA_STAGE_MANAGEMENT


def get_storage_account_name_for_request(
    request_type: str,
    status: AirlockRequestStatus,
    tre_id: str,
    short_workspace_id: str
) -> str:
    if use_metadata_stage_management():
        # Global workspace storage - all workspaces use same account
        if request_type == constants.IMPORT_TYPE:
            if status in [AirlockRequestStatus.Draft, AirlockRequestStatus.Submitted, AirlockRequestStatus.InReview]:
                # Core import stages
                return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE.format(tre_id)
            elif status in [AirlockRequestStatus.Approved, AirlockRequestStatus.ApprovalInProgress]:
                # Global workspace storage
                return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL.format(tre_id)
            elif status in [AirlockRequestStatus.Rejected, AirlockRequestStatus.RejectionInProgress,
                            AirlockRequestStatus.Blocked, AirlockRequestStatus.BlockingInProgress]:
                # These are in core storage
                return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE.format(tre_id)
        else:  # export
            if status in [AirlockRequestStatus.Approved, AirlockRequestStatus.ApprovalInProgress]:
                # Export approved in core
                return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE.format(tre_id)
            else:  # Draft, Submitted, InReview, Rejected, Blocked, etc.
                # Global workspace storage
                return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL.format(tre_id)
    else:
        # Legacy mode - return original separate account names
        if request_type == constants.IMPORT_TYPE:
            if status == AirlockRequestStatus.Draft:
                return constants.STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL.format(tre_id)
            elif status in [AirlockRequestStatus.Submitted, AirlockRequestStatus.InReview]:
                return constants.STORAGE_ACCOUNT_NAME_IMPORT_INPROGRESS.format(tre_id)
            elif status in [AirlockRequestStatus.Approved, AirlockRequestStatus.ApprovalInProgress]:
                return constants.STORAGE_ACCOUNT_NAME_IMPORT_APPROVED.format(short_workspace_id)
            elif status in [AirlockRequestStatus.Rejected, AirlockRequestStatus.RejectionInProgress]:
                return constants.STORAGE_ACCOUNT_NAME_IMPORT_REJECTED.format(tre_id)
            elif status in [AirlockRequestStatus.Blocked, AirlockRequestStatus.BlockingInProgress]:
                return constants.STORAGE_ACCOUNT_NAME_IMPORT_BLOCKED.format(tre_id)
        else:  # export
            if status == AirlockRequestStatus.Draft:
                return constants.STORAGE_ACCOUNT_NAME_EXPORT_INTERNAL.format(short_workspace_id)
            elif status in [AirlockRequestStatus.Submitted, AirlockRequestStatus.InReview]:
                return constants.STORAGE_ACCOUNT_NAME_EXPORT_INPROGRESS.format(short_workspace_id)
            elif status in [AirlockRequestStatus.Approved, AirlockRequestStatus.ApprovalInProgress]:
                return constants.STORAGE_ACCOUNT_NAME_EXPORT_APPROVED.format(tre_id)
            elif status in [AirlockRequestStatus.Rejected, AirlockRequestStatus.RejectionInProgress]:
                return constants.STORAGE_ACCOUNT_NAME_EXPORT_REJECTED.format(short_workspace_id)
            elif status in [AirlockRequestStatus.Blocked, AirlockRequestStatus.BlockingInProgress]:
                return constants.STORAGE_ACCOUNT_NAME_EXPORT_BLOCKED.format(short_workspace_id)


def get_stage_from_status(request_type: str, status: AirlockRequestStatus) -> str:
    if request_type == constants.IMPORT_TYPE:
        if status == AirlockRequestStatus.Draft:
            return constants.STAGE_IMPORT_EXTERNAL
        elif status in [AirlockRequestStatus.Submitted, AirlockRequestStatus.InReview]:
            return constants.STAGE_IMPORT_IN_PROGRESS
        elif status in [AirlockRequestStatus.Approved, AirlockRequestStatus.ApprovalInProgress]:
            return constants.STAGE_IMPORT_APPROVED
        elif status in [AirlockRequestStatus.Rejected, AirlockRequestStatus.RejectionInProgress]:
            return constants.STAGE_IMPORT_REJECTED
        elif status in [AirlockRequestStatus.Blocked, AirlockRequestStatus.BlockingInProgress]:
            return constants.STAGE_IMPORT_BLOCKED
    else:  # export
        if status == AirlockRequestStatus.Draft:
            return constants.STAGE_EXPORT_INTERNAL
        elif status in [AirlockRequestStatus.Submitted, AirlockRequestStatus.InReview]:
            return constants.STAGE_EXPORT_IN_PROGRESS
        elif status in [AirlockRequestStatus.Approved, AirlockRequestStatus.ApprovalInProgress]:
            return constants.STAGE_EXPORT_APPROVED
        elif status in [AirlockRequestStatus.Rejected, AirlockRequestStatus.RejectionInProgress]:
            return constants.STAGE_EXPORT_REJECTED
        elif status in [AirlockRequestStatus.Blocked, AirlockRequestStatus.BlockingInProgress]:
            return constants.STAGE_EXPORT_BLOCKED

    # Default fallback
    return "unknown"
