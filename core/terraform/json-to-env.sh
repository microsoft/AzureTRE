#!/bin/bash
set -e
set -o pipefail

echo "# Generated environment variables from tf output"

jq -ers '
    if length != 1 or (.[0] | type) != "object" then
        error("Expected one Terraform output object. Check the state and regenerate core/tre_output.json.")
    else
        .[0]
    end
    |
    [
        {
            "path": "core_resource_group_name",
            "env_var": "RESOURCE_GROUP_NAME"
        },
        {
            "path": "core_resource_group_location",
            "env_var": "RESOURCE_LOCATION"
        },
        {
            "path": "app_gateway_name",
            "env_var": "APPLICATION_GATEWAY"
        },
        {
            "path": "static_web_storage",
            "env_var": "STORAGE_ACCOUNT"
        },
        {
            "path": "keyvault_name",
            "env_var": "KEYVAULT"
        },
        {
            "path": "keyvault_uri",
            "env_var": "KEYVAULT_URI"
        },
        {
            "path": "keyvault_resource_id",
            "env_var": "KEYVAULT_RESOURCE_ID"
        },
        {
            "path": "azure_tre_fqdn",
            "env_var": "FQDN"
        },
        {
            "path": "service_bus_resource_id",
            "env_var": "SERVICE_BUS_RESOURCE_ID"
        },
        {
            "path": "service_bus_namespace_fqdn",
            "env_var": "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE"
        },
        {
            "path": "service_bus_workspace_queue",
            "env_var": "SERVICE_BUS_RESOURCE_REQUEST_QUEUE"
        },
        {
            "path": "service_bus_deployment_status_queue",
            "env_var": "SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE"
        },
        {
            "path": "service_bus_step_result_queue",
            "env_var": "SERVICE_BUS_STEP_RESULT_QUEUE"
        },
        {
            "path": "state_store_resource_id",
            "env_var": "STATE_STORE_RESOURCE_ID"
        },
        {
            "path": "cosmosdb_mongo_resource_id",
            "env_var": "COSMOSDB_MONGO_RESOURCE_ID"
        },

        {
            "path": "state_store_account_name",
            "env_var": "COSMOSDB_ACCOUNT_NAME"
        },
        {
            "path": "cosmosdb_mongo_account_name",
            "env_var": "COSMOSDB_MONGO_ACCOUNT_NAME"
        },
        {
            "path": "state_store_endpoint",
            "env_var": "STATE_STORE_ENDPOINT"
        },
        {
            "path": "app_insights_connection_string",
            "env_var": "APPLICATIONINSIGHTS_CONNECTION_STRING"
        },
        {
            "path": "mgmt_storage_account_name",
            "env_var": "MGMT_STORAGE_ACCOUNT_NAME"
        },
        {
            "path": "mgmt_resource_group_name",
            "env_var": "MGMT_RESOURCE_GROUP_NAME"
        },
        {
            "path": "terraform_state_container_name",
            "env_var": "TERRAFORM_STATE_CONTAINER_NAME"
        },
        {
            "path": "registry_server",
            "env_var": "REGISTRY_SERVER"
        },
        {
            "path": "event_grid_status_changed_topic_endpoint",
            "env_var": "EVENT_GRID_STATUS_CHANGED_TOPIC_ENDPOINT"
        },
        {
            "path": "event_grid_airlock_notification_topic_endpoint",
            "env_var": "EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_ENDPOINT"
        },
        {
            "path": "event_grid_status_changed_topic_resource_id",
            "env_var": "EVENT_GRID_STATUS_CHANGED_TOPIC_RESOURCE_ID"
        },
        {
            "path": "event_grid_airlock_notification_topic_resource_id",
            "env_var": "EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_RESOURCE_ID"
        },
        {
            # This mapping is retained for older caches but is not a root output.
            "path": "airlock_malware_scan_result_topic_name",
            "env_var": "AIRLOCK_MALWARE_SCAN_RESULT_TOPIC_NAME",
            "optional": true
        }
    ]
        as $env_vars_to_extract
    |
    . as $outputs
    |
    $env_vars_to_extract
    |
    map(
        . as $mapping
        | if $mapping.optional and ($outputs | has($mapping.path) | not) then
            empty
        else
            $outputs[$mapping.path]
            | if type != "object" then
                error("Missing or invalid Terraform output: \($mapping.path). Check the state and regenerate core/tre_output.json.")
            elif (.value | type) != "string" then
                error("Terraform output \($mapping.path) must have a string value. Check the state and regenerate core/tre_output.json.")
            elif (.value | test("\\S") | not) then
                error("Terraform output \($mapping.path) is empty. Check the state and regenerate core/tre_output.json.")
            else
                "\($mapping.env_var)=\(.value | @sh)"
            end
        end
    )
    |
    .[]
    '
