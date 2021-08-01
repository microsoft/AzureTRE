resource "azurerm_network_interface" "internal" {
  name                = "internal-nic-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name

  ip_configuration {
    name                          = "primary"
    subnet_id                     = data.azurerm_subnet.dsvms.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_network_security_group" "dsvmnsg" {
  name                = "nsg-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
}

resource "azurerm_network_security_rule" "allow-rdp-inbound-from-vnet-dsvm" {
  name                        = "RDP"
  priority                    = 1010
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = 3389
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "*"
  network_security_group_name = azurerm_network_security_group.dsvmnsg.name
  resource_group_name         = data.azurerm_resource_group.ws.name
}

resource "azurerm_network_security_rule" "deny-all-inbound-override-dsvm" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Inbound"
  name                        = "deny-inbound-override"
  network_security_group_name = azurerm_network_security_group.dsvmnsg.name
  priority                    = 900
  protocol                    = "*"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "deny-outbound-override-dsvm" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Outbound"
  name                        = "deny-outbound-override"
  network_security_group_name = azurerm_network_security_group.dsvmnsg.name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_interface_security_group_association" "dev_vm_nsg_association" {
  network_interface_id      = azurerm_network_interface.internal.id
  network_security_group_id = azurerm_network_security_group.dsvmnsg.id
}

resource "random_string" "username" {
  length      = 4
  upper       = true
  lower       = true
  number      = true
  min_numeric = 1
  min_lower   = 1
  special     = false
}

resource "random_password" "password" {
  length           = 16
  lower            = true
  min_lower        = 1
  upper            = true
  min_upper        = 1
  number           = true
  min_numeric      = 1
  special          = true
  min_special      = 1
  override_special = "_%@"
}

resource "azurerm_virtual_machine" "dsvm" {
  name                             = local.vm_name
  location                         = data.azurerm_resource_group.ws.location
  resource_group_name              = data.azurerm_resource_group.ws.name
  network_interface_ids            = [azurerm_network_interface.internal.id]
  vm_size                          = "Standard_DS1_v2"
  delete_os_disk_on_termination    = false
  delete_data_disks_on_termination = false

  storage_image_reference {
    publisher = "microsoft-dsvm"
    offer     = "dsvm-windows"
    sku       = "server-2016"
    version   = "latest"
  }

  storage_os_disk {
    name              = "osdisk-${local.vm_name}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  os_profile {
    computer_name  = local.vm_name
    admin_username = random_string.username.result
    admin_password = random_password.password.result
  }

  os_profile_windows_config {
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    parent_service_id = var.guacamole_parent_service_id
  }
}
