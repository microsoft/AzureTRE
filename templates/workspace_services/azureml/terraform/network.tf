resource "azurerm_network_security_group" "aml" {
  location            = data.azurerm_virtual_network.ws.location
  name                = "nsg-aml-${local.short_service_id}"
  resource_group_name = data.azurerm_virtual_network.ws.resource_group_name
  tags                = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
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
  body = {
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
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_subnet" "aml" {
  name                 = "AMLSubnet${local.short_service_id}"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
  address_prefixes     = [var.address_space]

  # need to be disabled for AML private compute
  private_endpoint_network_policies             = "Disabled"
  private_link_service_network_policies_enabled = false

  service_endpoints = [
    "Microsoft.Storage"
  ]
  service_endpoint_policy_ids = [azapi_resource.aml_service_endpoint_policy.id]
}

resource "azurerm_subnet_network_security_group_association" "aml" {
  network_security_group_id = azurerm_network_security_group.aml.id
  subnet_id                 = azurerm_subnet.aml.id
}


resource "azurerm_network_security_rule" "allow_inbound_within_workspace_vnet" {
  access                       = "Allow"
  destination_port_range       = "*"
  destination_address_prefixes = data.azurerm_virtual_network.ws.address_space
  source_address_prefixes      = data.azurerm_virtual_network.ws.address_space
  direction                    = "Inbound"
  name                         = "inbound-within-workspace-vnet"
  network_security_group_name  = azurerm_network_security_group.aml.name
  priority                     = 100
  protocol                     = "*"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_port_range            = "*"
}

resource "azurerm_network_security_rule" "allow_batch_inbound" {
  count                       = var.is_exposed_externally ? 1 : 0
  access                      = "Allow"
  destination_port_ranges     = ["29876", "29877"]
  destination_address_prefix  = "VirtualNetwork"
  source_address_prefix       = "BatchNodeManagement"
  direction                   = "Inbound"
  name                        = "${local.short_service_id}-batch-inbound-29876"
  network_security_group_name = azurerm_network_security_group.aml.name
  priority                    = 101
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_aml_inbound" {
  count                       = var.is_exposed_externally ? 1 : 0
  access                      = "Allow"
  destination_port_ranges     = ["44224"]
  destination_address_prefix  = "VirtualNetwork"
  source_address_prefix       = "AzureMachineLearning"
  direction                   = "Inbound"
  name                        = "${local.short_service_id}-aml-inbound"
  network_security_group_name = azurerm_network_security_group.aml.name
  priority                    = 102
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
  network_security_group_name = azurerm_network_security_group.aml.name
  priority                    = 103
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_to_shared_services" {
  access                       = "Allow"
  destination_address_prefixes = data.azurerm_subnet.shared.address_prefixes
  destination_port_range       = "*"
  direction                    = "Outbound"
  name                         = "to-shared-services"
  network_security_group_name  = azurerm_network_security_group.aml.name
  priority                     = 104
  protocol                     = "*"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_address_prefix        = "*"
  source_port_range            = "*"
}


resource "azurerm_network_security_rule" "allow_outbound_to_internet" {
  access                      = "Allow"
  destination_address_prefix  = "INTERNET"
  destination_port_range      = "443"
  direction                   = "Outbound"
  name                        = "to-internet"
  network_security_group_name = azurerm_network_security_group.aml.name
  priority                    = 105
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_to_aml_udp_5831" {
  access                      = "Allow"
  destination_address_prefix  = "AzureMachineLearning"
  destination_port_range      = "5831"
  direction                   = "Outbound"
  name                        = "to-aml-udp"
  network_security_group_name = azurerm_network_security_group.aml.name
  priority                    = 106
  protocol                    = "Udp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_to_aml_tcp_443" {
  access                      = "Allow"
  destination_address_prefix  = "AzureMachineLearning"
  destination_port_range      = "443"
  direction                   = "Outbound"
  name                        = "to-aml-tcp-443"
  network_security_group_name = azurerm_network_security_group.aml.name
  priority                    = 107
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_to_aml_tcp_8787" {
  access                      = "Allow"
  destination_address_prefix  = "AzureMachineLearning"
  destination_port_range      = "8787"
  direction                   = "Outbound"
  name                        = "to-aml-tcp-8787-rstudio"
  network_security_group_name = azurerm_network_security_group.aml.name
  priority                    = 108
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_to_aml_tcp_18881" {
  access                      = "Allow"
  destination_address_prefix  = "AzureMachineLearning"
  destination_port_range      = "18881"
  direction                   = "Outbound"
  name                        = "to-aml-tcp-18881-language-server"
  network_security_group_name = azurerm_network_security_group.aml.name
  priority                    = 109
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_within_workspace_vnet" {
  access                       = "Allow"
  destination_port_range       = "*"
  destination_address_prefixes = data.azurerm_virtual_network.ws.address_space
  source_address_prefixes      = data.azurerm_virtual_network.ws.address_space
  direction                    = "Outbound"
  name                         = "outbound-within-workspace-subnet"
  network_security_group_name  = azurerm_network_security_group.aml.name
  priority                     = 100
  protocol                     = "*"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_port_range            = "*"
}

resource "azurerm_network_security_rule" "deny_outbound_override" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Outbound"
  name                        = "deny-outbound-override"
  network_security_group_name = azurerm_network_security_group.aml.name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}



resource "azurerm_network_security_rule" "deny_all_inbound_override" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Inbound"
  name                        = "deny-inbound-override"
  network_security_group_name = azurerm_network_security_group.aml.name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_route_table" "aml" {
  count                         = var.is_exposed_externally ? 1 : 0
  name                          = "rt-aml-${var.tre_id}-${local.short_service_id}"
  resource_group_name           = data.azurerm_resource_group.ws.name
  location                      = data.azurerm_resource_group.ws.location
  bgp_route_propagation_enabled = true
  tags                          = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }

}

resource "azurerm_route" "firewall" {
  count                  = var.is_exposed_externally ? 1 : 0
  name                   = "rt-firewall-${var.tre_id}-${local.short_service_id}"
  resource_group_name    = data.azurerm_resource_group.ws.name
  route_table_name       = azurerm_route_table.aml[count.index].name
  address_prefix         = data.azurerm_route_table.rt.route[0].address_prefix
  next_hop_type          = data.azurerm_route_table.rt.route[0].next_hop_type
  next_hop_in_ip_address = data.azurerm_route_table.rt.route[0].next_hop_in_ip_address
}

resource "azurerm_route" "aml" {
  count               = var.is_exposed_externally ? 1 : 0
  name                = "rt-aml-${var.tre_id}-${local.short_service_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
  route_table_name    = azurerm_route_table.aml[count.index].name
  address_prefix      = "AzureMachineLearning"
  next_hop_type       = "Internet"
}

resource "azurerm_route" "batch" {
  count               = var.is_exposed_externally ? 1 : 0
  name                = "rt-batch-${var.tre_id}-${local.short_service_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
  route_table_name    = azurerm_route_table.aml[count.index].name
  address_prefix      = "BatchNodeManagement"
  next_hop_type       = "Internet"
}


resource "azurerm_subnet_route_table_association" "rt_aml_subnet_association" {
  count          = var.is_exposed_externally ? 1 : 0
  route_table_id = azurerm_route_table.aml[count.index].id
  subnet_id      = azurerm_subnet.aml.id
}

resource "azurerm_subnet_route_table_association" "rt_core_aml_subnet_association" {
  count          = var.is_exposed_externally ? 0 : 1
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.aml.id
}
