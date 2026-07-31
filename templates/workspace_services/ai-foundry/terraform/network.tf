# All resources in this file are part of the Foundry Agent Service (Standard
# Setup) and are only created when the agent service is enabled.

# Network Security Group for AI Foundry Agents
resource "azurerm_network_security_group" "agents" {
  count               = var.enable_agent_service ? 1 : 0
  location            = data.azurerm_virtual_network.ws.location
  name                = "nsg-aif-agents-${local.short_service_id}"
  resource_group_name = data.azurerm_virtual_network.ws.resource_group_name
  tags                = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

# Agent subnet with Microsoft.App/environments delegation for AI Foundry agents
resource "azurerm_subnet" "agents" {
  count                = var.enable_agent_service ? 1 : 0
  name                 = "AIFAgentSubnet${local.short_service_id}"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
  address_prefixes     = [var.address_space]

  private_endpoint_network_policies = "Disabled"

  # Required delegation for AI Foundry Standard Agents with VNet injection
  delegation {
    name = "Microsoft.App.environments"

    service_delegation {
      name = "Microsoft.App/environments"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action"
      ]
    }
  }
}

resource "azurerm_subnet_network_security_group_association" "agents" {
  count                     = var.enable_agent_service ? 1 : 0
  network_security_group_id = azurerm_network_security_group.agents[0].id
  subnet_id                 = azurerm_subnet.agents[0].id
}

# NSG Rules for AI Foundry Agents

resource "azurerm_network_security_rule" "allow_inbound_within_workspace_vnet" {
  count                        = var.enable_agent_service ? 1 : 0
  access                       = "Allow"
  destination_port_range       = "*"
  destination_address_prefixes = data.azurerm_virtual_network.ws.address_space
  source_address_prefixes      = data.azurerm_virtual_network.ws.address_space
  direction                    = "Inbound"
  name                         = "inbound-within-workspace-vnet"
  network_security_group_name  = azurerm_network_security_group.agents[0].name
  priority                     = 100
  protocol                     = "*"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_port_range            = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_within_workspace_vnet" {
  count                        = var.enable_agent_service ? 1 : 0
  access                       = "Allow"
  destination_port_range       = "*"
  destination_address_prefixes = data.azurerm_virtual_network.ws.address_space
  source_address_prefixes      = data.azurerm_virtual_network.ws.address_space
  direction                    = "Outbound"
  name                         = "outbound-within-workspace-vnet"
  network_security_group_name  = azurerm_network_security_group.agents[0].name
  priority                     = 100
  protocol                     = "*"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_port_range            = "*"
}

# Allow outbound to services subnet (for accessing TRE resources and private endpoints)
resource "azurerm_network_security_rule" "allow_outbound_to_services" {
  count                        = var.enable_agent_service ? 1 : 0
  access                       = "Allow"
  destination_address_prefixes = data.azurerm_subnet.services.address_prefixes
  destination_port_range       = "*"
  direction                    = "Outbound"
  name                         = "to-services-subnet"
  network_security_group_name  = azurerm_network_security_group.agents[0].name
  priority                     = 101
  protocol                     = "*"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_address_prefix        = "*"
  source_port_range            = "*"
}

# Allow outbound HTTPS for AI Foundry agents to access Azure services
resource "azurerm_network_security_rule" "allow_outbound_https" {
  count                       = var.enable_agent_service ? 1 : 0
  access                      = "Allow"
  destination_address_prefix  = "INTERNET"
  destination_port_range      = "443"
  direction                   = "Outbound"
  name                        = "to-internet-https"
  network_security_group_name = azurerm_network_security_group.agents[0].name
  priority                    = 102
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

# Deny all other outbound traffic (data exfiltration prevention)
resource "azurerm_network_security_rule" "deny_outbound_override" {
  count                       = var.enable_agent_service ? 1 : 0
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Outbound"
  name                        = "deny-outbound-override"
  network_security_group_name = azurerm_network_security_group.agents[0].name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

# Deny all inbound from outside the VNet
resource "azurerm_network_security_rule" "deny_all_inbound_override" {
  count                       = var.enable_agent_service ? 1 : 0
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Inbound"
  name                        = "deny-inbound-override"
  network_security_group_name = azurerm_network_security_group.agents[0].name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

# Associate the agent subnet with the workspace route table (routes through firewall)
resource "azurerm_subnet_route_table_association" "agents" {
  count          = var.enable_agent_service ? 1 : 0
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.agents[0].id
}

# The AI Foundry account's "agent" network injection creates a platform-managed
# serviceAssociationLink ("legionservicelink", linkedResourceType
# Microsoft.App/environments) on the agent subnet. On uninstall the account is
# deleted first, but the platform removes that link asynchronously (observed
# ~5-10 minutes later). Deleting the subnet before the link is gone fails with
# InUseSubnetCannotBeDeleted. This sleep only elapses on destroy: the account
# depends on it (so the account is deleted first), and it depends on the subnet
# (so it is torn down before the subnet), giving the platform time to release the
# subnet after account deletion and before the subnet itself is removed.
resource "time_sleep" "wait_for_subnet_release" {
  count            = var.enable_agent_service ? 1 : 0
  destroy_duration = "600s"

  depends_on = [azurerm_subnet.agents]
}
