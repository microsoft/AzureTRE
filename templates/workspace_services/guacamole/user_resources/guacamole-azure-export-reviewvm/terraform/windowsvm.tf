resource "azurerm_network_interface" "internal" {
  name                = "internal-nic-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  tags                = local.tre_user_resources_tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = data.azurerm_subnet.services.id
    private_ip_address_allocation = "Dynamic"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_network_security_group" "vm_nsg" {
  name                = "vm-nsg-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  tags                = local.tre_user_resources_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_network_security_rule" "allow_outbound_airlock_exip_storage_pe" {
  access = "Allow"
  # Should this be a list?
  destination_address_prefixes = [for pe in data.azurerm_private_endpoint_connection.airlock_export_inprogress_pe.private_service_connection : pe.private_ip_address]
  destination_port_range       = "*"
  direction                    = "Outbound"
  name                         = "allow-airlock-exip-storage-pe"
  network_security_group_name  = azurerm_network_security_group.vm_nsg.name
  priority                     = 101
  protocol                     = "*"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_address_prefixes      = azurerm_windows_virtual_machine.windowsvm.private_ip_addresses
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
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefixes     = azurerm_windows_virtual_machine.windowsvm.private_ip_addresses
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_webapps_to_vm" {
  access = "Allow"
  destination_port_ranges = [
    "80",
    "443",
    "445",
    "3306",
    "3389",
    "5432",
  ]
  destination_address_prefixes = azurerm_windows_virtual_machine.windowsvm.private_ip_addresses
  source_address_prefixes      = data.azurerm_subnet.webapps.address_prefixes
  direction                    = "Outbound"
  name                         = "outbound-from-webapps-to-vm"
  network_security_group_name  = azurerm_network_security_group.vm_nsg.name
  priority                     = 140
  protocol                     = "Tcp"
  resource_group_name          = data.azurerm_resource_group.ws.name
  source_port_range            = "*"
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
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefixes     = azurerm_windows_virtual_machine.windowsvm.private_ip_addresses
  source_port_range           = "*"
}

resource "azurerm_network_interface_security_group_association" "nsg_association" {
  network_interface_id      = azurerm_network_interface.internal.id
  network_security_group_id = azurerm_network_security_group.vm_nsg.id
}

resource "random_string" "username" {
  length      = 4
  upper       = true
  lower       = true
  numeric     = true
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
  numeric          = true
  min_numeric      = 1
  special          = true
  min_special      = 1
  override_special = "_%@"
}

resource "azurerm_windows_virtual_machine" "windowsvm" {
  name                       = local.vm_name
  location                   = data.azurerm_resource_group.ws.location
  resource_group_name        = data.azurerm_resource_group.ws.name
  network_interface_ids      = [azurerm_network_interface.internal.id]
  size                       = local.vm_sizes[var.vm_size]
  allow_extension_operations = true
  admin_username             = random_string.username.result
  admin_password             = random_password.password.result

  custom_data = base64encode(data.template_file.download_review_data_script.rendered)

  # set source_image_id/reference depending on the config for the selected image
  source_image_id = local.selected_image_source_id
  dynamic "source_image_reference" {
    for_each = local.selected_image_source_refs
    content {
      publisher = source_image_reference.value["publisher"]
      offer     = source_image_reference.value["offer"]
      sku       = source_image_reference.value["sku"]
      version   = source_image_reference.value["version"]
    }
  }

  os_disk {
    name                 = "osdisk-${local.vm_name}"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tre_user_resources_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_virtual_machine_extension" "config_script" {
  name                 = "${azurerm_windows_virtual_machine.windowsvm.name}-vmextension"
  virtual_machine_id   = azurerm_windows_virtual_machine.windowsvm.id
  publisher            = "Microsoft.Compute"
  type                 = "CustomScriptExtension"
  type_handler_version = "1.10"
  tags                 = local.tre_user_resources_tags

  protected_settings = <<PROT
    {
      "commandToExecute": "powershell -ExecutionPolicy Unrestricted -NoProfile -NonInteractive -command \"cp c:/azuredata/customdata.bin c:/azuredata/configure.ps1; c:/azuredata/configure.ps1 \""
    }
PROT

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "windowsvm_password" {
  name         = "${local.vm_name}-admin-credentials"
  value        = "${random_string.username.result}\n${random_password.password.result}"
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.tre_user_resources_tags

  lifecycle { ignore_changes = [tags] }
}

data "template_file" "download_review_data_script" {
  template = file("${path.module}/download_review_data.ps1")
  vars = {
    airlock_request_sas_url = var.airlock_request_sas_url
  }
}

