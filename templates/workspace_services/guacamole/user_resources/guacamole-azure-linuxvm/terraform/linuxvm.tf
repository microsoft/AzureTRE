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

resource "azurerm_linux_virtual_machine" "linuxvm" {
  name                            = local.vm_name
  location                        = data.azurerm_resource_group.ws.location
  resource_group_name             = data.azurerm_resource_group.ws.name
  network_interface_ids           = [azurerm_network_interface.internal.id]
  size                            = local.vm_sizes[var.vm_size]
  disable_password_authentication = false
  admin_username                  = random_string.username.result
  admin_password                  = random_password.password.result

  custom_data = data.template_cloudinit_config.config.rendered

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

data "template_cloudinit_config" "config" {
  gzip          = true
  base64_encode = true

  part {
    content_type = "text/x-shellscript"
    content      = data.template_file.get_apt_keys.rendered
  }

  part {
    content_type = "text/cloud-config"
    content      = data.template_file.apt_sources_config.rendered
  }

  part {
    content_type = "text/x-shellscript"
    content      = data.template_file.pypi_sources_config.rendered
  }

  part {
    content_type = "text/x-shellscript"
    content      = data.template_file.vm_config.rendered
  }
}

data "template_file" "vm_config" {
  template = file("${path.module}/vm_config.sh")
  vars = {
    INSTALL_UI            = local.selected_image.install_ui ? 1 : 0
    SHARED_STORAGE_ACCESS = tobool(var.shared_storage_access) ? 1 : 0
    STORAGE_ACCOUNT_NAME  = data.azurerm_storage_account.stg.name
    STORAGE_ACCOUNT_KEY   = data.azurerm_storage_account.stg.primary_access_key
    HTTP_ENDPOINT         = data.azurerm_storage_account.stg.primary_file_endpoint
    FILESHARE_NAME        = var.shared_storage_access ? data.azurerm_storage_share.shared_storage[0].name : ""
    NEXUS_PROXY_URL       = local.nexus_proxy_url
    CONDA_CONFIG          = local.selected_image.conda_config ? 1 : 0
    VM_USER               = random_string.username.result
    APT_SKU               = replace(local.apt_sku, ".", "")
  }
}

data "template_file" "get_apt_keys" {
  template = file("${path.module}/get_apt_keys.sh")
  vars = {
    NEXUS_PROXY_URL = local.nexus_proxy_url
  }
}

data "template_file" "pypi_sources_config" {
  template = file("${path.module}/pypi_sources_config.sh")
  vars = {
    nexus_proxy_url = local.nexus_proxy_url
  }
}

data "template_file" "apt_sources_config" {
  template = file("${path.module}/apt_sources_config.yml")
  vars = {
    nexus_proxy_url = local.nexus_proxy_url
    apt_sku         = local.apt_sku
  }
}

resource "azurerm_key_vault_secret" "linuxvm_password" {
  name         = local.vm_password_secret_name
  value        = "${random_string.username.result}\n${random_password.password.result}"
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.tre_user_resources_tags

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_storage_account" "stg" {
  name                = local.storage_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_storage_share" "shared_storage" {
  count                = var.shared_storage_access ? 1 : 0
  name                 = var.shared_storage_name
  storage_account_name = data.azurerm_storage_account.stg.name
}
