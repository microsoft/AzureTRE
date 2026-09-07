from core import config
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.resource import Resource
from models.schemas.resource import ResourcePatch
from services.logging import logger


def _truncate_ids(resource_ids: list[str], limit: int = 25) -> list[str]:
    if len(resource_ids) <= limit:
        return resource_ids
    return resource_ids[:limit]


def ensure_workspace_airlock_version_supported(properties: dict, default_version: int = 1) -> None:
    """Reject unsupported airlock versions. A missing airlock_version means legacy (v1)."""
    if not properties:
        return
    if not properties.get("enable_airlock", True):
        return

    airlock_version = properties.get("airlock_version", default_version)

    if not config.ENABLE_LEGACY_AIRLOCK and airlock_version == 1:
        raise ValueError(
            "Cannot use airlock_version=1 because legacy airlock is disabled in core "
            "(enable_legacy_airlock=false). Use airlock_version=2."
        )


async def ensure_airlock_version_change_allowed(workspace: Resource, resource_patch: ResourcePatch, request_repo: AirlockRequestRepository) -> None:
    """Reject version changes while airlock requests are still in flight."""
    if not resource_patch.properties:
        return
    current_version = workspace.properties.get("airlock_version", 1)
    if current_version >= 2 and workspace.properties.get("enable_airlock", True) and resource_patch.properties.get("enable_airlock") is False:
        # The v2 signer and its conditioned role assignment are needed to delete request containers
        # retained in shared storage. Workspace deletion performs that cleanup before removing them.
        logger.warning("Blocked Airlock disablement for v2 workspace %s", workspace.id)
        raise ValueError(
            "Cannot disable Airlock on an airlock_version=2 workspace because doing so would remove "
            "the signer required to clean up request data. Delete the workspace to remove Airlock data safely."
        )
    if "airlock_version" not in resource_patch.properties:
        return
    new_version = resource_patch.properties["airlock_version"]
    if type(new_version) is not int or new_version not in (1, 2):
        raise ValueError("airlock_version must be an integer with a value of 1 or 2")
    if new_version == current_version:
        return

    if new_version < current_version:
        # Downgrading destroys the v2 signer and conditioned role assignments that guard existing
        # shared containers, with no path to re-grant access to data created under v2.
        logger.warning("Blocked airlock_version downgrade %s->%s for workspace %s", current_version, new_version, workspace.id)
        raise ValueError(
            f"Cannot change airlock_version from {current_version} to {new_version}: downgrading is not "
            f"supported because it removes access to data created under the newer version."
        )

    request_ids = await request_repo.get_in_flight_airlock_request_ids_for_workspace(workspace.id)
    if request_ids:
        logger.warning(
            "Blocked airlock_version change %s->%s for workspace %s due to %d in-flight airlock request(s)",
            current_version, new_version, workspace.id, len(request_ids)
        )
        raise ValueError(
            f"Cannot change airlock_version from {current_version} to {new_version} while "
            f"{len(request_ids)} airlock request(s) are still in progress in this workspace "
            f"(their data would be left behind in the previous version's storage). "
            f"Let them complete or cancel them first. Request ids: {_truncate_ids(request_ids)}"
        )
