data "local_file" "version" {
  filename = "${path.module}/../../../../resource_processor/_version.py"
}

data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

data "cloudinit_config" "config" {
  gzip          = true
  base64_encode = true

  part {
    content_type = "text/cloud-config"
    content      = local.cloudconfig_content
  }
}

data "azurerm_key_vault_key" "tre_encryption" {
  count        = var.enable_cmk_encryption ? 1 : 0
  name         = var.kv_encryption_key_name
  key_vault_id = var.key_store_id
}
