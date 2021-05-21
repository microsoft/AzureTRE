#!/bin/bash
set -e

docker build -t "${TF_VAR_resource_name_prefix}acr.azurecr.io/microsoft/azuretre/management-api:${TF_VAR_image_tag}" ./core/api/