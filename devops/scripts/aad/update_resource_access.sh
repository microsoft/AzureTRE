#!/bin/bash

# This script is designed to be `source`d to create reusable helper functions

# Utility function that retrieves all of the 'requiredResourceAccess' from an application,
# it then removes any access for a given `resourceAppId`, merges in a new element into the
# array and then posts it back to AAD.
function update_resource_access()
{
  local msGraphUri=$1
  local existingObjectId=$2
  local resourceAppId=$3
  local requiredResourceAccessArray=$4

  # Get the existing required resource access from the automation app,
  # but remove the access that we are about to add for idempotency. We cant use
  # the response from az cli as it returns an 'AdditionalProperties' element in
  # the json
  existingResourceAccess=$(az rest \
    --method GET \
    --uri "${msGraphUri}/applications/${existingObjectId}" \
    --headers Content-Type=application/json -o json \
    | jq -r --arg resourceAppId "${resourceAppId}" \
    'del(.requiredResourceAccess[] | select(.resourceAppId==$resourceAppId)) | .requiredResourceAccess' \
    )

  # Add the existing resource access so we don't remove any existing permissions.
  combinedResourceAccess=$(jq -c . << JSON
{
  "requiredResourceAccess": ${requiredResourceAccessArray},
  "existingAccess": ${existingResourceAccess}
}
JSON
)

  # Manipulate the json (add existingAccess into requiredResourceAccess and then remove it)
  requiredResourceAccess=$(echo "${combinedResourceAccess}" | \
    jq '.requiredResourceAccess += .existingAccess | {requiredResourceAccess}')

  az rest --method PATCH \
    --uri "${msGraphUri}/applications/${existingObjectId}" \
    --headers Content-Type=application/json \
    --body "${requiredResourceAccess}"
}
