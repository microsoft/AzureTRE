# Network Security Group for AI Foundry Agents
resource "azurerm_network_security_group" "agents" {
  location            = data.azurerm_virtual_network.ws.location
  name                = "nsg-aif-agents-${local.short_service_id}"
  resource_group_name = data.azurerm_virtual_network.ws.resource_group_name
  tags                = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

# Agent subnet with Microsoft.App/environments delegation for AI Foundry agents
resource "azurerm_subnet" "agents" {
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
  network_security_group_id = azurerm_network_security_group.agents.id
  subnet_id                 = azurerm_subnet.agents.id
}

# NSG Rules for AI Foundry Agents

resource "azurerm_network_security_rule" "allow_inbound_within_workspace_vnet" {
  access                       = "Allow"
  destination_port_range       = "*"
  destination_address_prefixes = data.azurerm_virtual_network.ws.address_space
  source_address_prefixes      = data.azurerm_virtual_network.ws.address_space
  direction                    = "Inbound"
  name                         = "inbound-within-workspace-vnet"
  network_security_group_name  = azurerm_network_security_group.agents.name
  priority                     = 100
  protocol                     = "*"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_port_range            = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_within_workspace_vnet" {
  access                       = "Allow"
  destination_port_range       = "*"
  destination_address_prefixes = data.azurerm_virtual_network.ws.address_space
  source_address_prefixes      = data.azurerm_virtual_network.ws.address_space
  direction                    = "Outbound"
  name                         = "outbound-within-workspace-vnet"
  network_security_group_name  = azurerm_network_security_group.agents.name
  priority                     = 100
  protocol                     = "*"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_port_range            = "*"
}

# Allow outbound to services subnet (for accessing TRE resources and private endpoints)
resource "azurerm_network_security_rule" "allow_outbound_to_services" {
  access                       = "Allow"
  destination_address_prefixes = data.azurerm_subnet.services.address_prefixes
  destination_port_range       = "*"
  direction                    = "Outbound"
  name                         = "to-services-subnet"
  network_security_group_name  = azurerm_network_security_group.agents.name
  priority                     = 101
  protocol                     = "*"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_address_prefix        = "*"
  source_port_range            = "*"
}

# Allow outbound HTTPS for AI Foundry agents to access Azure services
resource "azurerm_network_security_rule" "allow_outbound_https" {
  access                      = "Allow"
  destination_address_prefix  = "INTERNET"
  destination_port_range      = "443"
  direction                   = "Outbound"
  name                        = "to-internet-https"
  network_security_group_name = azurerm_network_security_group.agents.name
  priority                    = 102
  protocol                    = "Tcp"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

# Deny all other outbound traffic (data exfiltration prevention)
resource "azurerm_network_security_rule" "deny_outbound_override" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Outbound"
  name                        = "deny-outbound-override"
  network_security_group_name = azurerm_network_security_group.agents.name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

# Deny all inbound from outside the VNet
resource "azurerm_network_security_rule" "deny_all_inbound_override" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Inbound"
  name                        = "deny-inbound-override"
  network_security_group_name = azurerm_network_security_group.agents.name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

# Associate the agent subnet with the workspace route table (routes through firewall)
resource "azurerm_subnet_route_table_association" "agents" {
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.agents.id
}
