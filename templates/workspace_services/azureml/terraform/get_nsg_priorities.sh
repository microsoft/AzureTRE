#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset


eval "$(jq -r '@sh "nsg_name=\(.nsg_name) resource_group_name=\(.resource_group_name) nsg_rule_name=\(.nsg_rule_name) direction=\(.direction)"')"

# This variables are loaded in for us
# shellcheck disable=SC2154
if NSG_RULE=$(az network nsg rule show -g "$resource_group_name" --nsg-name "$nsg_name" --name "$nsg_rule_name" -o json); then
    NSG_RULE_PRIORITY=$(echo "$NSG_RULE" | jq '.priority')
else
  # shellcheck disable=SC2016
    NSG_RULE_MAX_PRIORITY=$(az network nsg rule list -g "$resource_group_name" --nsg-name  "$nsg_name" --query 'not_null(max_by([?direction==`Outbound` && access==`Allow`],&priority).priority) || `100`')
    NSG_RULE_PRIORITY=$($NSG_RULE_MAX_PRIORITY + 1)
fi

# Safely produce a JSON object containing the result value.
jq -n --arg nsg_rule_priority "$NSG_RULE_PRIORITY"  '{ "nsg_rule_priority":$nsg_rule_priority }'
