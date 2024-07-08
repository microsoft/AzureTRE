#!/bin/bash

# This script is designed to be `source`d to create reusable helper functions

function convert_azure_env_to_arm_env()
{
  azure_environment=$1
  declare -A arm_envs=( ["AzureCloud"]="public" ["AzureUSGovernment"]="usgovernment")
  echo "${arm_envs[${azure_environment}]}"
}
