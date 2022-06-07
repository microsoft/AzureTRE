#!/bin/bash
export TF_LOG=""

terraform init -input=false -backend=true -reconfigure \
    -backend-config="resource_group_name=rg-terraform" \
    -backend-config="storage_account_name=stanpatfstate" \
    -backend-config="container_name=tfstate" \
    -backend-config="key=tfstate.databricks"

terraform plan

terraform apply -auto-approve
