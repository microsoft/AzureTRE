#!/bin/bash

PLAN_FILE="devops.tfplan"

terraform init -input=false -backend=true -reconfigure -upgrade
terraform plan -out ${PLAN_FILE}
terraform apply -auto-approve ${PLAN_FILE}
