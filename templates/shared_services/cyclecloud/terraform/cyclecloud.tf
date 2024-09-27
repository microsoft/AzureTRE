

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

# Using old resource due to - https://github.com/hashicorp/terraform-provider-azurerm/issues/6117
resource "azurerm_virtual_machine" "cyclecloud" {
  name                             = local.vm_name
  location                         = data.azurerm_resource_group.rg.location
  resource_group_name              = data.azurerm_resource_group.rg.name
  network_interface_ids            = [azurerm_network_interface.cyclecloud.id]
  vm_size                          = "Standard_DS3_v2"
  delete_os_disk_on_termination    = true
  delete_data_disks_on_termination = true

  os_profile_linux_config {
    disable_password_authentication = false
  }

  os_profile {
    computer_name  = local.vm_name
    admin_username = random_string.username.result
    admin_password = random_password.password.result
  }

  storage_image_reference {
    publisher = "azurecyclecloud"
    offer     = "azure-cyclecloud"
    sku       = "cyclecloud8"
    version   = "latest"
  }

  plan {
    publisher = "azurecyclecloud"
    name      = "cyclecloud8"
    product   = "azure-cyclecloud"
  }

  storage_os_disk {
    name              = "${local.vm_name}-osdisk"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Premium_LRS"
  }


  identity {
    type = "SystemAssigned"
  }

  tags = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_key_vault_secret" "cyclecloud_password" {
  name         = "${local.vm_name}-admin-credentials"
  value        = "${random_string.username.result}\n${random_password.password.result}"
  key_vault_id = data.azurerm_key_vault.core.id
  tags         = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_subscription" "primary" {
}

# could change to RG contributor and sub reader
resource "azurerm_role_assignment" "subscription_contributor" {
  scope                = data.azurerm_subscription.primary.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_virtual_machine.cyclecloud.identity[0].principal_id
}

resource "azurerm_network_interface" "cyclecloud" {
  name                = "nic-cyclecloud-${var.tre_id}-${local.short_service_id}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = local.core_resource_group_name
  tags                = local.tre_shared_service_tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = data.azurerm_subnet.shared.id
    private_ip_address_allocation = "Dynamic"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "cyclecloud" {
  name                = "cyclecloud-${data.azurerm_public_ip.app_gateway_ip.fqdn}"
  resource_group_name = local.core_resource_group_name
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "cyclecloud_core_vnet" {
  name                  = "cyclecloudlink-core"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.cyclecloud.name
  virtual_network_id    = data.azurerm_virtual_network.core.id
  tags                  = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_a_record" "cyclecloud_vm" {
  name                = "@"
  zone_name           = azurerm_private_dns_zone.cyclecloud.name
  resource_group_name = local.core_resource_group_name
  ttl                 = 300
  records             = [azurerm_network_interface.cyclecloud.private_ip_address]
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

