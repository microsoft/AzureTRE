#!/bin/bash

set -e

eval "$(jq -r '@sh "firewall_name=\(.firewall_name) resource_group_name=\(.resource_group_name) collection_name_suffix=\(.collection_name_suffix)"')"

if NETWORK_RULES=$(az network firewall network-rule list -g $resource_group_name -f  $firewall_name --collection-name "nrc-$collection_name_suffix" -o json); then
    NETWORK_RULE_PRIORITY=$(echo $NETWORK_RULES | jq '.priority')
else
    NETWORK_RULE_MAX_PRIORITY=$(az network firewall network-rule collection list -f $firewall_name -g $resource_group_name -o json --query 'not_null(max_by([],&priority).priority) || `100`')
    NETWORK_RULE_PRIORITY=$(($NETWORK_RULE_MAX_PRIORITY+1))
fi

if APPLICATION_RULES=$(az network firewall application-rule list -g $resource_group_name -f  $firewall_name --collection-name "arc-$collection_name_suffix" -o json); then
    APPLICATION_RULE_PRIORITY=$(echo $APPLICATION_RULES | jq '.priority')
else
    APPLICATION_RULE_MAX_PRIORITY=$(az network firewall application-rule collection list -f $firewall_name -g $resource_group_name -o json --query 'not_null(max_by([],&priority).priority) || `100`')
    APPLICATION_RULE_PRIORITY=$(($APPLICATION_RULE_MAX_PRIORITY+1))
fi

# Safely produce a JSON object containing the result value.
jq -n --arg network_rule_priority "$NETWORK_RULE_PRIORITY" --arg application_rule_priority "$APPLICATION_RULE_PRIORITY" '{ "network_rule_priority":$network_rule_priority, "application_rule_priority":$application_rule_priority }'