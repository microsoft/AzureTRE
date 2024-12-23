data "azurerm_key_vault_certificates" "certificates" {
  key_vault_id = var.keyvault_id
}

resource "null_resource" "internal_certs" {
  provisioner "local-exec" {
    command = "${path.root}/certificate_internals.sh"
    environment = {
      CA_CERT_EXISTS = contains(data.azurerm_key_vault_certificates.certificates.names, "${local.keyvault_cert_prefix}-${local.ca_common_name}") ? 1 : 0
      CA_COMMON_NAME = local.ca_common_name
      LEAF_IPS       = join(" ", local.internal_agw_ips_max)
      KV_NAME        = split("/", var.keyvault_id)[8]
      KV_CERT_PREFIX = local.keyvault_cert_prefix
    }
    working_dir = path.module
  }
  triggers = {
    always_run = timestamp()
  }
}

data "azurerm_key_vault_secrets" "secrets" {
  key_vault_id = var.keyvault_id
  depends_on   = [null_resource.internal_certs]
}
