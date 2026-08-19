import os
import logging
from datetime import datetime, UTC
from typing import Dict, List, Optional

from azure.core import MatchConditions
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError, ResourceModifiedError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import HttpResponseError


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.{get_storage_endpoint_suffix()}/"


def get_storage_endpoint_suffix() -> str:
    return os.environ.get("STORAGE_ENDPOINT_SUFFIX", "core.windows.net")


def get_credential():
    managed_identity = os.environ.get("MANAGED_IDENTITY_CLIENT_ID")
    if managed_identity:
        logging.info("using the Airlock processor's managed identity to get credentials.")
        return DefaultAzureCredential(managed_identity_client_id=managed_identity,
                                      exclude_shared_token_cache_credential=True)
    return DefaultAzureCredential()


def create_container_with_metadata(account_name: str, request_id: str, stage: str,
                                   workspace_id: str = None, request_type: str = None,
                                   created_by: str = None) -> None:
    try:
        container_name = request_id
        blob_service_client = BlobServiceClient(
            account_url=get_account_url(account_name),
            credential=get_credential()
        )

        metadata = {
            "stage": stage,
            "stage_history": stage,
            "created_at": datetime.now(UTC).isoformat(),
            "last_stage_change": datetime.now(UTC).isoformat(),
        }

        if workspace_id:
            metadata["workspace_id"] = workspace_id
        if request_type:
            metadata["request_type"] = request_type
        if created_by:
            metadata["created_by"] = created_by

        container_client = blob_service_client.get_container_client(container_name)
        container_client.create_container(metadata=metadata)

        logging.info(f'Container created for request id: {request_id} with stage: {stage}')

    except ResourceExistsError:
        logging.info(f'Did not create a new container. Container already exists for request id: {request_id}.')


def update_container_stage(account_name: str, request_id: str, new_stage: str,
                           changed_by: str = None, additional_metadata: Dict[str, str] = None,
                           skip_if_stage_in: Optional[List[str]] = None,
                           max_attempts: int = 5) -> bool:
    """Update stage metadata with optimistic concurrency."""
    container_name = request_id
    blob_service_client = BlobServiceClient(
        account_url=get_account_url(account_name),
        credential=get_credential()
    )
    container_client = blob_service_client.get_container_client(container_name)

    for attempt in range(1, max_attempts + 1):
        try:
            properties = container_client.get_container_properties()
        except ResourceNotFoundError:
            logging.error(f"Container {request_id} not found in account {account_name}")
            raise

        metadata = properties.metadata.copy()
        old_stage = metadata.get('stage', 'unknown')

        if skip_if_stage_in and old_stage in skip_if_stage_in:
            logging.info(
                f"Container {request_id} already at stage '{old_stage}', not moving it to '{new_stage}'"
            )
            return False

        metadata['stage'] = new_stage
        stage_history = metadata.get('stage_history', old_stage)
        metadata['stage_history'] = f"{stage_history},{new_stage}"
        metadata['last_stage_change'] = datetime.now(UTC).isoformat()
        if changed_by:
            metadata['last_changed_by'] = changed_by
        if additional_metadata:
            metadata.update(additional_metadata)

        try:
            container_client.set_container_metadata(
                metadata,
                etag=properties.etag,
                match_condition=MatchConditions.IfNotModified
            )
        except ResourceModifiedError:
            logging.warning(
                f"Container {request_id} metadata changed concurrently (attempt {attempt}/{max_attempts}), retrying"
            )
            continue
        except HttpResponseError as e:
            logging.error(f"Failed to update container metadata: {str(e)}")
            raise

        logging.info(
            f"Updated container {request_id} from stage '{old_stage}' to '{new_stage}' in account {account_name}"
        )
        return True

    raise HttpResponseError(
        message=f"Could not update stage for container {request_id} after {max_attempts} attempts due to concurrent updates"
    )


def get_container_metadata(account_name: str, request_id: str) -> Dict[str, str]:
    container_name = request_id
    blob_service_client = BlobServiceClient(
        account_url=get_account_url(account_name),
        credential=get_credential()
    )
    container_client = blob_service_client.get_container_client(container_name)

    try:
        properties = container_client.get_container_properties()
        return properties.metadata
    except ResourceNotFoundError:
        logging.error(f"Container {request_id} not found in account {account_name}")
        raise
