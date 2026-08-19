from resources import constants
from models.domain.airlock_request import AirlockRequestStatus


def get_storage_account_name_for_request(
    request_type: str,
    status: AirlockRequestStatus,
    tre_id: str
) -> str:
    if request_type == constants.IMPORT_TYPE:
        if status in [AirlockRequestStatus.Approved, AirlockRequestStatus.ApprovalInProgress]:
            return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL.format(tre_id)
        return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE.format(tre_id)

    if status in [AirlockRequestStatus.Approved, AirlockRequestStatus.ApprovalInProgress]:
        return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_CORE.format(tre_id)
    return constants.STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE_GLOBAL.format(tre_id)
