"""
Blob operations with metadata-based stage management.

This module provides functions for managing airlock containers using metadata
to track stages instead of copying data between storage accounts.
"""
import os
import logging
import json
from datetime import datetime, timedelta, UTC
from typing import Tuple, Dict, Optional

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import ContainerSasPermissions, generate_container_sas, BlobServiceClient
from azure.core.exceptions import HttpResponseError

from exceptions import NoFilesInRequestException, TooManyFilesInRequestException


def get_account_url(account_name: str) -> str:
    return f"https://{account_name}.blob.{get_storage_endpoint_suffix()}/"


def get_storage_endpoint_suffix() -> str:
    """Get the storage endpoint suffix from environment."""
    return os.environ.get("STORAGE_ENDPOINT_SUFFIX", "core.windows.net")


def get_credential():
    """Get Azure credential for authentication."""
    return DefaultAzureCredential()


def create_container_with_metadata(account_name: str, request_id: str, stage: str, 
                                   workspace_id: str = None, request_type: str = None,
                                   created_by: str = None) -> None:
    """
    Create a container with initial stage metadata.
    
    Args:
        account_name: Storage account name
        request_id: Unique request identifier (used as container name)
        stage: Initial stage (e.g., 'import-external', 'export-internal')
        workspace_id: Workspace ID (optional)
        request_type: 'import' or 'export' (optional)
        created_by: User who created the request (optional)
    """
    try:
        container_name = request_id
        blob_service_client = BlobServiceClient(
            account_url=get_account_url(account_name),
            credential=get_credential()
        )
        
        # Prepare initial metadata
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
            
        # Create container with metadata
        container_client = blob_service_client.get_container_client(container_name)
        container_client.create_container(metadata=metadata)
        
        logging.info(f'Container created for request id: {request_id} with stage: {stage}')
        
    except ResourceExistsError:
        logging.info(f'Did not create a new container. Container already exists for request id: {request_id}.')


def update_container_stage(account_name: str, request_id: str, new_stage: str, 
                          changed_by: str = None, additional_metadata: Dict[str, str] = None) -> None:
    """
    Update container stage metadata instead of copying data.
    
    This replaces the copy_data() function for metadata-based stage management.
    
    Args:
        account_name: Storage account name
        request_id: Unique request identifier (container name)
        new_stage: New stage to transition to
        changed_by: User/system that triggered the stage change
        additional_metadata: Additional metadata to add/update (e.g., scan_result)
    """
    try:
        container_name = request_id
        blob_service_client = BlobServiceClient(
            account_url=get_account_url(account_name),
            credential=get_credential()
        )
        container_client = blob_service_client.get_container_client(container_name)
        
        # Get current metadata
        try:
            properties = container_client.get_container_properties()
            metadata = properties.metadata.copy()
        except ResourceNotFoundError:
            logging.error(f"Container {request_id} not found in account {account_name}")
            raise
        
        # Track old stage for logging
        old_stage = metadata.get('stage', 'unknown')
        
        # Update stage metadata
        metadata['stage'] = new_stage
        
        # Update stage history
        stage_history = metadata.get('stage_history', old_stage)
        metadata['stage_history'] = f"{stage_history},{new_stage}"
        
        # Update timestamp
        metadata['last_stage_change'] = datetime.now(UTC).isoformat()
        
        # Track who made the change
        if changed_by:
            metadata['last_changed_by'] = changed_by
        
        # Add any additional metadata (e.g., scan results)
        if additional_metadata:
            metadata.update(additional_metadata)
        
        # Apply the updated metadata
        container_client.set_container_metadata(metadata)
        
        logging.info(
            f"Updated container {request_id} from stage '{old_stage}' to '{new_stage}' in account {account_name}"
        )
        
    except HttpResponseError as e:
        logging.error(f"Failed to update container metadata: {str(e)}")
        raise


def get_container_stage(account_name: str, request_id: str) -> str:
    """
    Get the current stage of a container.
    
    Args:
        account_name: Storage account name
        request_id: Unique request identifier (container name)
        
    Returns:
        Current stage from container metadata
    """
    container_name = request_id
    blob_service_client = BlobServiceClient(
        account_url=get_account_url(account_name),
        credential=get_credential()
    )
    container_client = blob_service_client.get_container_client(container_name)
    
    try:
        properties = container_client.get_container_properties()
        return properties.metadata.get('stage', 'unknown')
    except ResourceNotFoundError:
        logging.error(f"Container {request_id} not found in account {account_name}")
        raise


def get_container_metadata(account_name: str, request_id: str) -> Dict[str, str]:
    """
    Get all metadata for a container.
    
    Args:
        account_name: Storage account name
        request_id: Unique request identifier (container name)
        
    Returns:
        Dictionary of all container metadata
    """
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


def get_blob_client_from_blob_info(storage_account_name: str, container_name: str, blob_name: str):
    """Get blob client for a specific blob."""
    source_blob_service_client = BlobServiceClient(
        account_url=get_account_url(storage_account_name),
        credential=get_credential()
    )
    source_container_client = source_blob_service_client.get_container_client(container_name)
    return source_container_client.get_blob_client(blob_name)


def get_request_files(account_name: str, request_id: str) -> list:
    """
    Get list of files in a request container.
    
    Args:
        account_name: Storage account name
        request_id: Unique request identifier (container name)
        
    Returns:
        List of files with name and size
    """
    files = []
    blob_service_client = BlobServiceClient(
        account_url=get_account_url(account_name),
        credential=get_credential()
    )
    container_client = blob_service_client.get_container_client(container=request_id)

    for blob in container_client.list_blobs():
        files.append({"name": blob.name, "size": blob.size})

    return files


def delete_container_by_request_id(account_name: str, request_id: str) -> None:
    """
    Delete a container and all its contents.
    
    Args:
        account_name: Storage account name
        request_id: Unique request identifier (container name)
    """
    try:
        container_name = request_id
        blob_service_client = BlobServiceClient(
            account_url=get_account_url(account_name),
            credential=get_credential()
        )
        container_client = blob_service_client.get_container_client(container_name)
        container_client.delete_container()
        
        logging.info(f"Deleted container {request_id} from account {account_name}")
        
    except ResourceNotFoundError:
        logging.warning(f"Container {request_id} not found in account {account_name}, may have been already deleted")
    except HttpResponseError as e:
        logging.error(f"Failed to delete container: {str(e)}")
        raise
