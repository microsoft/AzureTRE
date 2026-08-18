from core import config
from db.repositories.airlock_requests import AirlockRequestRepository
from db.repositories.workspaces import WorkspaceRepository
from models.domain.resource import Resource
from models.schemas.resource import ResourcePatch
from services.logging import logger


def _truncate_ids(resource_ids: list[str], limit: int = 25) -> list[str]:
    if len(resource_ids) <= limit:
        return resource_ids
    return resource_ids[:limit]


def ensure_workspace_airlock_version_supported(properties: dict) -> None:
    """Block creating a legacy (airlock_version=1) workspace when core legacy airlock is
    disabled (v2-only). Fails fast before deployment instead of deploying a workspace
    whose airlock would be non-functional (the core v1 storage accounts do not exist).

    Raises ValueError so the API returns HTTP 400.
    """
    if config.ENABLE_LEGACY_AIRLOCK:
        return
    if not properties:
        return
    if properties.get("enable_airlock") and properties.get("airlock_version") == 1:
        raise ValueError(
            "Cannot create a workspace with airlock_version=1 because legacy airlock is disabled "
            "in core (enable_legacy_airlock=false). Use airlock_version=2."
        )


async def ensure_airlock_version_change_allowed(workspace: Resource, resource_patch: ResourcePatch, request_repo: AirlockRequestRepository) -> None:
    """Block changing a workspace's airlock_version while it has in-flight airlock requests.

    Changing the version transitions the workspace between the v1 and v2 airlock storage
    modules; the previous version's storage accounts are destroyed, which would strand any
    in-flight request stamped with the old version.

    Raises ValueError so the API returns HTTP 400.
    """
    if not resource_patch.properties:
        return
    new_version = resource_patch.properties.get("airlock_version")
    if new_version is None:
        return
    current_version = workspace.properties.get("airlock_version", 1)
    if new_version == current_version:
        return

    in_flight_request_ids = await request_repo.get_in_flight_airlock_request_ids_for_workspace(workspace.id)
    if in_flight_request_ids:
        logger.warning(
            "Blocked airlock_version change %s->%s for workspace %s due to %d in-flight airlock request(s)",
            current_version, new_version, workspace.id, len(in_flight_request_ids)
        )
        raise ValueError(
            f"Cannot change airlock_version from {current_version} to {new_version} while "
            f"{len(in_flight_request_ids)} in-flight airlock request(s) exist in this workspace. "
            f"Complete, cancel or revoke them first. Request ids: {_truncate_ids(in_flight_request_ids)}"
        )


async def run_legacy_airlock_migration_guard() -> None:
    """At startup, warn (or block) when legacy airlock is disabled but active v1 workspaces or
    in-flight v1 requests still exist, since disabling legacy airlock removes the v1 storage
    accounts their data lives in.
    """
    if config.ENABLE_LEGACY_AIRLOCK:
        return

    workspace_repo = await WorkspaceRepository.create()
    request_repo = await AirlockRequestRepository.create()

    # Backfill airlock_version on pre-v2 workspaces/requests first, so the guard evaluates real
    # persisted versions instead of treating every missing value as v1, and so it isn't a startup
    # deadlock: the backfill runs in-process here rather than depending on the external db-migrate
    # call (which needs the API to already be healthy).
    await workspace_repo.set_default_airlock_version_for_legacy_workspaces()
    await request_repo.set_default_airlock_version_for_legacy_requests()

    v1_workspace_ids = await workspace_repo.get_active_v1_workspace_ids()
    v1_in_flight_request_ids = await request_repo.get_in_flight_v1_airlock_request_ids()

    if not (v1_workspace_ids or v1_in_flight_request_ids):
        logger.info("Legacy airlock migration guard check passed. enable_legacy_airlock=false and no active v1 dependencies were found")
        return

    warning_message = (
        "Legacy airlock migration guard detected active v1 dependencies while enable_legacy_airlock=false. "
        "Disabling legacy airlock can remove v1 storage accounts and cause data loss"
    )
    logger.warning(
        "%s | v1_workspace_count=%d v1_in_flight_request_count=%d v1_workspace_ids=%s v1_in_flight_request_ids=%s",
        warning_message, len(v1_workspace_ids), len(v1_in_flight_request_ids),
        _truncate_ids(v1_workspace_ids), _truncate_ids(v1_in_flight_request_ids)
    )

    if config.BLOCK_DISABLE_LEGACY_AIRLOCK_IF_V1_EXISTS:
        raise RuntimeError(
            f"{warning_message}. Set ENABLE_LEGACY_AIRLOCK=true, finish migration to airlock_version=2, "
            "or set BLOCK_DISABLE_LEGACY_AIRLOCK_IF_V1_EXISTS=false to continue with warning-only behavior"
        )
