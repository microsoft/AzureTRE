#!/bin/bash
export TF_LOG=""

terraform init -input=false -backend=true -reconfigure -upgrade \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name:?}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name:?}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name:?}" \
    -backend-config="key=${TRE_ID:?}-shared-service-sonatype-nexus"

terraform destroy -auto-approve
