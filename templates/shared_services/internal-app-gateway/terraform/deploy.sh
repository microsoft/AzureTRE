#!/bin/bash
set -e

export TF_LOG=""
# This script assumes you have created an .env from the sample and the variables
# will come from there.
# shellcheck disable=SC2154
terraform init -input=false -reconfigure
terraform plan
terraform apply -auto-approve
