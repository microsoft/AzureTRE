#!/bin/bash

# Parameters
tre_id=$1
workspace_id=$2
workspace_service_id=$3
user_resource_id=$4

# Build the tag filter query
tag_filters="--tag tre_resource_id=$tre_id"
[ -n "$workspace_id" ] && tag_filters="$tag_filters --tag tre_workspace_id=$workspace_id"
[ -n "$workspace_service_id" ] && tag_filters="$tag_filters --tag tre_workspace_service_id=$workspace_service_id"
[ -n "$user_resource_id" ] && tag_filters="$tag_filters --tag tre_user_resource_id=$user_resource_id"

# login to azure
az login --identity

# Get the resource IDs with the specified tags
resource_ids=$(az resource list "$tag_filters" --query "[].id" -o tsv)

# Delete the resources
if [ -n "$resource_ids" ]; then
  az resource delete --ids "$resource_ids" --yes
else
  echo "No resources found with the specified tags."
fi
