from core import config
from db.repositories.airlock_requests import AirlockRequestRepository
from db.repositories.workspaces import WorkspaceRepository
from services.logging import logger


def _truncate_ids(resource_ids: list[str], limit: int = 25) -> list[str]:
    if len(resource_ids) <= limit:
        return resource_ids
    return resource_ids[:limit]


async def run_legacy_airlock_migration_guard() -> None:
    if config.ENABLE_LEGACY_AIRLOCK:
        return

    workspace_repo = await WorkspaceRepository.create()
    request_repo = await AirlockRequestRepository.create()

    v1_workspace_ids = await workspace_repo.get_active_v1_workspace_ids()
    v1_in_flight_request_ids = await request_repo.get_in_flight_v1_airlock_request_ids()

    has_v1_dependencies = bool(v1_workspace_ids or v1_in_flight_request_ids)
    if not has_v1_dependencies:
        logger.info("Legacy airlock migration guard check passed. enable_legacy_airlock=false and no active v1 dependencies were found")
        return

    warning_message = (
        "Legacy airlock migration guard detected active v1 dependencies while enable_legacy_airlock=false. "
        "Disabling legacy airlock can remove v1 storage accounts and cause data loss"
    )

    logger.warning(
        "%s | v1_workspace_count=%d v1_in_flight_request_count=%d v1_workspace_ids=%s v1_in_flight_request_ids=%s",
        warning_message,
        len(v1_workspace_ids),
        len(v1_in_flight_request_ids),
        _truncate_ids(v1_workspace_ids),
        _truncate_ids(v1_in_flight_request_ids)
    )

    if config.BLOCK_DISABLE_LEGACY_AIRLOCK_IF_V1_EXISTS:
        raise RuntimeError(
            f"{warning_message}. Set ENABLE_LEGACY_AIRLOCK=true, finish migration to airlock_version=2, "
            "or set BLOCK_DISABLE_LEGACY_AIRLOCK_IF_V1_EXISTS=false to continue with warning-only behavior"
        )
