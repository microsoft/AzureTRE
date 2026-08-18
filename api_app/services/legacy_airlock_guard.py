from core import config
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.resource import Resource
from models.schemas.resource import ResourcePatch
from resources import constants
from services.logging import logger


def _truncate_ids(resource_ids: list[str], limit: int = 25) -> list[str]:
    if len(resource_ids) <= limit:
        return resource_ids
    return resource_ids[:limit]


def ensure_workspace_airlock_version_supported(properties: dict) -> None:
    """Reject unsupported airlock versions."""
    if not properties:
        return
    if not properties.get("enable_airlock", True):
        return

    airlock_version = properties.get("airlock_version", constants.DEFAULT_AIRLOCK_VERSION)

    if not config.ENABLE_LEGACY_AIRLOCK and airlock_version == 1:
        raise ValueError(
            "Cannot use airlock_version=1 because legacy airlock is disabled in core "
            "(enable_legacy_airlock=false). Use airlock_version=2."
        )


async def ensure_airlock_version_change_allowed(workspace: Resource, resource_patch: ResourcePatch, request_repo: AirlockRequestRepository) -> None:
    """Reject version changes while airlock requests retain data."""
    if not resource_patch.properties:
        return
    new_version = resource_patch.properties.get("airlock_version")
    if new_version is None:
        return
    current_version = workspace.properties.get("airlock_version", 1)
    if new_version == current_version:
        return

    request_ids = await request_repo.get_data_retaining_airlock_request_ids_for_workspace(workspace.id)
    if request_ids:
        logger.warning(
            "Blocked airlock_version change %s->%s for workspace %s due to %d airlock request(s) with retained data",
            current_version, new_version, workspace.id, len(request_ids)
        )
        raise ValueError(
            f"Cannot change airlock_version from {current_version} to {new_version} while "
            f"{len(request_ids)} airlock request(s) with retained data exist in this workspace "
            f"(the previous version's storage accounts, and their approved-import links/data, would be destroyed). "
            f"Export or remove them first. Request ids: {_truncate_ids(request_ids)}"
        )
