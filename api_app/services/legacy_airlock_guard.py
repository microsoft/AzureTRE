from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.resource import Resource
from models.schemas.resource import ResourcePatch
from services.logging import logger


def _truncate_ids(resource_ids: list[str], limit: int = 25) -> list[str]:
    if len(resource_ids) <= limit:
        return resource_ids
    return resource_ids[:limit]


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
