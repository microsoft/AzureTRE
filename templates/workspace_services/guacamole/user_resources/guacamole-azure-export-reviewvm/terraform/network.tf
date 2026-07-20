# Airlock export review VMs need outbound access to the in-progress export
# storage account private endpoint and to the web apps subnet. The rest of the
# VM Terraform is shared via the ./vm module; this file holds the
# export-specific networking.

data "azurerm_subnet" "webapps" {
  name                 = "WebAppsSubnet"
  virtual_network_name = module.windows_vm.virtual_network_name
  resource_group_name  = module.windows_vm.resource_group_name
}

data "azurerm_private_endpoint_connection" "airlock_export_inprogress_pe" {
  name                = "pe-sa-export-ip-blob-${module.windows_vm.short_workspace_id}"
  resource_group_name = module.windows_vm.resource_group_name
}

# The shared services subnet hosts the Nexus package proxy that the shared
# vm_config.ps1 bootstrap uses to install the data science tooling.
data "azurerm_subnet" "shared" {
  provider             = azurerm.core
  name                 = "SharedSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = data.azurerm_resource_group.core.name
}

resource "azurerm_network_security_group" "vm_nsg" {
  name                = "vm-nsg-${module.windows_vm.service_resource_name_suffix}"
  location            = module.windows_vm.location
  resource_group_name = module.windows_vm.resource_group_name
  tags                = module.windows_vm.tre_user_resources_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_network_security_rule" "allow_outbound_airlock_exip_storage_pe" {
  access                       = "Allow"
  destination_address_prefixes = [for pe in data.azurerm_private_endpoint_connection.airlock_export_inprogress_pe.private_service_connection : pe.private_ip_address]
  destination_port_range       = "*"
  direction                    = "Outbound"
  name                         = "allow-airlock-exip-storage-pe"
  network_security_group_name  = azurerm_network_security_group.vm_nsg.name
  priority                     = 101
  protocol                     = "*"
  resource_group_name          = module.windows_vm.resource_group_name
  source_address_prefixes      = module.windows_vm.vm_private_ip_addresses
  source_port_range            = "*"
}

# Allow the review VM to reach the shared services (Nexus) subnet so the shared
# vm_config.ps1 bootstrap can install tooling from the Nexus proxy.
resource "azurerm_network_security_rule" "allow_outbound_to_shared_services" {
  access                       = "Allow"
  destination_address_prefixes = data.azurerm_subnet.shared.address_prefixes
  destination_port_range       = "*"
  direction                    = "Outbound"
  name                         = "to-shared-services"
  network_security_group_name  = azurerm_network_security_group.vm_nsg.name
  priority                     = 110
  protocol                     = "*"
  resource_group_name          = module.windows_vm.resource_group_name
  source_address_prefixes      = module.windows_vm.vm_private_ip_addresses
  source_port_range            = "*"
}

// Outbound traffic gets routed to the firewall
resource "azurerm_network_security_rule" "allow_outbound_to_internet" {
  access                      = "Allow"
  destination_address_prefix  = "INTERNET"
  destination_port_range      = "443"
  direction                   = "Outbound"
  name                        = "to-internet"
  network_security_group_name = azurerm_network_security_group.vm_nsg.name
  priority                    = 120
  protocol                    = "Tcp"
  resource_group_name         = module.windows_vm.resource_group_name
  source_address_prefixes     = module.windows_vm.vm_private_ip_addresses
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_inbound_webapps_to_vm" {
  access                       = "Allow"
  destination_address_prefixes = module.windows_vm.vm_private_ip_addresses
  destination_port_ranges = [
    "80",
    "443",
    "445",
    "3306",
    "3389",
    "5432",
  ]
  direction                   = "Inbound"
  name                        = "inbound-from-webapps-to-vm"
  network_security_group_name = azurerm_network_security_group.vm_nsg.name
  priority                    = 140
  protocol                    = "Tcp"
  resource_group_name         = module.windows_vm.resource_group_name
  source_address_prefixes     = data.azurerm_subnet.webapps.address_prefixes
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "deny_inbound_override" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Inbound"
  name                        = "deny-inbound-override"
  network_security_group_name = azurerm_network_security_group.vm_nsg.name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = module.windows_vm.resource_group_name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "deny_outbound_override" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Outbound"
  name                        = "deny-outbound-override"
  network_security_group_name = azurerm_network_security_group.vm_nsg.name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = module.windows_vm.resource_group_name
  source_address_prefixes     = module.windows_vm.vm_private_ip_addresses
  source_port_range           = "*"
}

resource "azurerm_network_interface_security_group_association" "nsg_association" {
  network_interface_id      = module.windows_vm.nic_id
  network_security_group_id = azurerm_network_security_group.vm_nsg.id
}
