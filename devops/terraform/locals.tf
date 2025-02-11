locals {
  # The key store for encryption keys could either be external or created by terraform
  key_store_id = var.enable_cmk_encryption ? (var.external_key_store_id != null ? var.external_key_store_id : azurerm_key_vault.encryption_kv[0].id) : null

  myip = var.public_deployment_ip_address != "" ? var.public_deployment_ip_address : chomp(data.http.myip[0].response_body)
}
