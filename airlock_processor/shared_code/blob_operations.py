import logging

import datetime
from azure.storage.blob import ContainerSasPermissions, generate_container_sas, BlobServiceClient

from exceptions.AirlockInvalidContainerException import AirlockInvalidContainerException


def copy_data(source_account_name: str, source_account_key: str, sa_source_connection_string: str, sa_dest_connection_string: str, request_id: str):
    container_name = request_id

    # token geneation with expiry of 1 hour. since its not shared, we can leave it to expire (no need to track/delete)
    sas_token = generate_container_sas(account_name=source_account_name,
                                       container_name=container_name,
                                       account_key=source_account_key,
                                       permission=ContainerSasPermissions(read=True),
                                       expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1))

    # Copy files
    source_blob_service_client = BlobServiceClient.from_connection_string(sa_source_connection_string)
    dest_blob_service_client = BlobServiceClient.from_connection_string(sa_dest_connection_string)

    source_container_client = source_blob_service_client.get_container_client(container_name)

    try:
        found_blobs = 0
        blob_name = ""
        for blob in source_container_client.list_blobs():
            if found_blobs > 0:
                msg = "Request with id {} contains more than 1 file. flow aborted.".format(request_id)
                logging.error(msg)
                raise AirlockInvalidContainerException(msg)
            blob_name = blob.name
            found_blobs += 1

        if found_blobs == 0:
            logging.info('Request with id %s did not contain any files. flow aborted.', request_id)

    except Exception:
        logging.error('Request with id %s failed.', request_id)
        raise()

    source_blob = source_container_client.get_blob_client(blob_name)

    source_url = f'{source_blob.url}?{sas_token}'
    # source_url = source_blob.url

    copied_blob = dest_blob_service_client.get_blob_client(container_name, source_blob.blob_name)
    copy = copied_blob.start_copy_from_url(source_url)
    
    try:
      logging.info("Copy operation returned 'copy_id': '%s', 'copy_status': '%s'", copy["copy_id"], copy["copy_status"])
    except KeyError as e:
      logging.error(f"Failed getting operation id and status {e}")
