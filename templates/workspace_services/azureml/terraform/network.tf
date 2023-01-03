
data "azurerm_network_security_group" "ws" {
  name                = "nsg-ws"
  resource_group_name = data.azurerm_resource_group.ws.name
}

# Using AzApi due to https://github.com/hashicorp/terraform-provider-azurerm/issues/14852
# resource "azurerm_subnet_service_endpoint_storage_policy" "aml" {
#   name                = "aml-service-endpoint-policy"
#   resource_group_name = data.azurerm_virtual_network.ws.resource_group_name
#   location            = data.azurerm_virtual_network.ws.location
#
#   definition {
#     name = "aml-service-endpoint-policy"
#     service_resources = [
#       azurerm_storage_account.aml.id,
#       "/services/Azure/MachineLearning"
#     ]
#   }
#
#   tags = local.tre_workspace_service_tags
# }

resource "azapi_resource" "aml_service_endpoint_policy" {
  type      = "Microsoft.Network/serviceEndpointPolicies@2022-05-01"
  name      = "aml-service-endpoint-policy-${local.short_service_id}"
  location  = data.azurerm_virtual_network.ws.location
  parent_id = data.azurerm_resource_group.ws.id
  tags      = local.tre_workspace_service_tags
  body = jsonencode({
    properties = {
      serviceEndpointPolicyDefinitions = [
        {
          name = "aml-service-endpoint-policy-definition-storage-${local.short_service_id}"
          properties = {
            service = "Microsoft.Storage"
            serviceResources = [
              azurerm_storage_account.aml.id
            ]
          }
          type = "Microsoft.Network/serviceEndpointPolicies/serviceEndpointPolicyDefinitions"
        },
        {
          name = "aml-service-endpoint-policy-definition-azureml-${local.short_service_id}"
          properties = {
            service = "Global"
            serviceResources = [
              "/services/Azure/MachineLearning"
            ]
          }
          type = "Microsoft.Network/serviceEndpointPolicies/serviceEndpointPolicyDefinitions"
        }
      ]
    }
  })
}

resource "null_resource" "az_login_sp" {

  count = var.arm_use_msi == true ? 0 : 1
  provisioner "local-exec" {
    command = "az login --service-principal --username ${var.arm_client_id} --password ${var.arm_client_secret} --tenant ${var.arm_tenant_id}"
  }

  triggers = {
    timestamp = timestamp()
  }

  # need to be disabled for AML private compute
  private_endpoint_network_policies_enabled     = false
  private_link_service_network_policies_enabled = false

  service_endpoints = [
    "Microsoft.Storage"
  ]
  service_endpoint_policy_ids = [azapi_resource.aml_service_endpoint_policy.id]
}

resource "null_resource" "az_login_msi" {

  count = var.arm_use_msi == true ? 1 : 0
  provisioner "local-exec" {
    command = "az login --identity -u '${data.azurerm_client_config.current.client_id}'"
  }

  triggers = {
    timestamp = timestamp()
  }
}

data "external" "nsg_rule_priorities_inbound" {
  program = ["bash", "-c", "./get_nsg_priorities.sh"]

  query = {
    nsg_name            = data.azurerm_network_security_group.ws.name
    resource_group_name = data.azurerm_resource_group.ws.name
    nsg_rule_name       = "${local.short_service_id}-aml-inbound"
    direction           = "Inbound"
  }
  depends_on = [
    null_resource.az_login_sp,
    null_resource.az_login_msi
  ]
}



data "external" "nsg_rule_priorities_outbound" {
  program = ["bash", "-c", "./get_nsg_priorities.sh"]

  query = {
    nsg_name            = data.azurerm_network_security_group.ws.name
    nsg_rule_name       = "${local.short_service_id}-allow-Outbound_Storage_445"
    resource_group_name = data.azurerm_resource_group.ws.name
    direction           = "Outbound"
  }
  depends_on = [
    null_resource.az_login_sp,
    null_resource.az_login_msi
  ]
}


resource "azurerm_network_security_rule" "allow_batch_inbound" {
  access                      = "Allow"
  destination_port_ranges     = ["29876"]
  destination_address_prefix  = "VirtualNetwork"
  source_address_prefix       = "BatchNodeManagement"
  direction                   = "Inbound"
  name                        = "${local.short_service_id}-batch-inbound-29876"
  network_security_group_name = data.azurerm_network_security_group.ws.name
  priority                    = tonumber(data.external.nsg_rule_priorities_inbound.result.nsg_rule_priority)
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_batch_inbound_29877" {
  count                       = var.is_exposed_externally ? 1 : 0
  access                      = "Allow"
  destination_port_ranges     = ["29877"]
  destination_address_prefix  = "VirtualNetwork"
  source_address_prefix       = "BatchNodeManagement"
  direction                   = "Inbound"
  name                        = "${local.short_service_id}-batch-inbound-29877"
  network_security_group_name = data.azurerm_network_security_group.ws.name
  priority                    = tonumber(data.external.nsg_rule_priorities_inbound.result.nsg_rule_priority) + 1
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_aml_inbound" {
  #count                       = var.is_exposed_externally ? 1 : 0
  access                      = "Allow"
  destination_port_ranges     = ["44224"]
  destination_address_prefix  = "VirtualNetwork"
  source_address_prefix       = "AzureMachineLearning"
  direction                   = "Inbound"
  name                        = "${local.short_service_id}-aml-inbound"
  network_security_group_name = data.azurerm_network_security_group.ws.name
  priority                    = tonumber(data.external.nsg_rule_priorities_inbound.result.nsg_rule_priority) + 2
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_storage_445" {
  count                       = var.is_exposed_externally ? 1 : 0
  access                      = "Allow"
  destination_port_range      = "445"
  destination_address_prefix  = "Storage"
  source_address_prefix       = "VirtualNetwork"
  direction                   = "Outbound"
  name                        = "${local.short_service_id}-allow-Outbound_Storage_445"
  network_security_group_name = data.azurerm_network_security_group.ws.name
  priority                    = tonumber(data.external.nsg_rule_priorities_outbound.result.nsg_rule_priority)
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}
