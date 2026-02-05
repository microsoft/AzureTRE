"""
Helper functions to support both legacy and consolidated airlock storage approaches.

This module provides wrapper functions that abstract the storage account logic,
allowing the API to work with either the legacy multi-account approach or the
new consolidated metadata-based approach using a feature flag.
"""
import os
from typing import Tuple
from models.domain.airlock_request import AirlockRequestStatus
from models.domain.workspace import Workspace
from resources import constants


def use_metadata_stage_management() -> bool:
    """
    Check if metadata-based stage management is enabled via feature flag.
    
    Returns:
        True if metadata-based approach should be used, False for legacy approach
    """
    return os.getenv('USE_METADATA_STAGE_MANAGEMENT', 'false').lower() == 'true'


def get_storage_account_name_for_request(
    request_type: str,
    status: AirlockRequestStatus,
    tre_id: str,
    short_workspace_id: str
) -> str:
    """
    Get the storage account name for an airlock request based on its type and status.
    
    In consolidated mode:
    - All core stages (import external, in-progress, rejected, blocked, export approved) → stalairlock
    - All workspace stages → stalairlockws
    
    In legacy mode, returns the original separate account names.
    
    Args:
        request_type: 'import' or 'export'
        status: Current status of the airlock request
        tre_id: TRE identifier
        short_workspace_id: Short workspace ID (last 4 characters)
        
    Returns:
        Storage account name for the given request state
    """
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
    """
    Map airlock request status to storage container stage metadata value.
    
    Args:
        request_type: 'import' or 'export'
        status: Current status of the airlock request
        
    Returns:
        Stage value for container metadata
    """
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
