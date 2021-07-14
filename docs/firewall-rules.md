# Adding Firewall Rules as part of a workspace or service deployment

A TRE service may require certian firewall rules to be opened in the TRE firewall. Examples include:

- Access to an external authorisation endpoint
- Access to an external data store
- Access to an external API

Please be aware when opening firewall rules there is the potential for data to be leaked from the workspace to the external location.

## Using Terraform to open firewall rules

Until a mechanism to update shared services has been implemented firewall rule updates should be done using terraform as part of the service deployment. The aim is to create a firewall rule that grants access from the workspace's address space to the external location. The challenge being the rule must use a priority that has not been used by any other rule.

1. Create a `firewall.tf` file in the `terraform` directory of the workspace.

1. Add the following code to the `firewall.tf` file to enable the TRE firewall and workspace netowrk to be referenced:

    ```hcl
    data "azurerm_firewall" "fw" {
        name                = "fw-${var.tre_id}"
        resource_group_name = "rg-${var.tre_id}"
    }

    data "azurerm_virtual_network" "ws" {
        name                = "vnet-${var.tre_id}-ws-${var.workspace_id}"
        resource_group_name = "rg-${var.tre_id}-ws-${var.workspace_id}"
    }
    ```

1. Define a local variable that contains the locations that access should be allowed to, and the naming format for the service resources for example:

    ```hcl
    locals {
        allowed_urls                     = ["*.anaconda.com", "*.anaconda.org"]
        service_resource_name_suffix    = "${var.tre_id}-ws-${var.workspace_id}-svc-${local.service_id}"
    }
    ```

1. Log into the Azure CLI using service principal details:

    ```hcl
    resource "null_resource" "az_login" {
        provisioner "local-exec" {
            command = "az login --service-principal -u '${var.arm_client_id}' -p '${var.arm_client_secret}' --tenant '${var.arm_tenant_id}'"
        }

        triggers = {
            timestamp = timestamp()
        }
    }
    ```

1. Call the `get_firewall_priorities.sh` script to find the next available priority:

    ```hcl
    data "external" "rule_priorities" {
        program = ["bash", "-c", "./get_firewall_priorities.sh"]

        query = {
            firewall_name       = data.azurerm_firewall.fw.name
            resource_group_name = data.azurerm_firewall.fw.resource_group_name
            service_resource_name_suffix = local.service_resource_name_suffix
        }
        depends_on = [
            null_resource.az_login
        ]
    }
    ```

1. Save the `get_firewall_priorities.sh` script as a file in the `terraform` directory:

    ```bash
    #!/bin/bash

    set -e

    eval "$(jq -r '@sh "firewall_name=\(.firewall_name) resource_group_name=\(.resource_group_name) service_resource_name_suffix=\(.service_resource_name_suffix)"')"

    if NETWORK_RULES=$(az network firewall network-rule list -g $resource_group_name -f  $firewall_name --collection-name "nrc-$service_resource_name_suffix" -o json); then
        NETWORK_RULE_PRIORITY=$(echo $NETWORK_RULES | jq '.priority')
    else
        NETWORK_RULE_MAX_PRIORITY=$(az network firewall network-rule collection list -f $firewall_name -g $resource_group_name -o json --query 'not_null(max_by([],&priority).priority) || `100`')
        NETWORK_RULE_PRIORITY=$(($NETWORK_RULE_MAX_PRIORITY+1))
    fi

    if APPLICATION_RULES=$(az network firewall application-rule list -g $resource_group_name -f  $firewall_name --collection-name "arc-$service_resource_name_suffix" -o json); then
        APPLICATION_RULE_PRIORITY=$(echo $APPLICATION_RULES | jq '.priority')
    else
        APPLICATION_RULE_MAX_PRIORITY=$(az network firewall application-rule collection list -f $firewall_name -g $resource_group_name -o json --query 'not_null(max_by([],&priority).priority) || `100`')
        APPLICATION_RULE_PRIORITY=$(($APPLICATION_RULE_MAX_PRIORITY+1))
    fi

    # Safely produce a JSON object containing the result value.
    jq -n --arg network_rule_priority "$NETWORK_RULE_PRIORITY" --arg application_rule_priority "$APPLICATION_RULE_PRIORITY" '{ "network_rule_priority":$network_rule_priority, "application_rule_priority":$application_rule_priority }'
    ```

1. Create the firwall rule using a resource similar to the below:

    ```hcl
    resource "azurerm_firewall_application_rule_collection" "apprulecollection" {
        name                = "arc-${local.service_resource_name_suffix}"
        azure_firewall_name = data.azurerm_firewall.fw.name
        resource_group_name = data.azurerm_firewall.fw.resource_group_name
        priority            = data.external.rule_priorities.result.application_rule_priority
        action              = "Allow"

        rule {
            name = "allowServiceXRules"

            source_addresses = data.azurerm_virtual_network.ws.address_space

            target_fqdns = local.allowed_urls

            protocol {
                port = "443"
                type = "Https"
            }
            protocol {
                port = "80"
                type = "Http"
            }
        }
    }
    ```
