resource "azurerm_role_assignment" "keyvault_appgwcerts_role" {
  scope                = data.azurerm_key_vault.key_vault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.agw_id.principal_id
}

resource "azurerm_key_vault_certificate" "tlscert" {
  name         = var.cert_name
  key_vault_id = data.azurerm_key_vault.key_vault.id
  tags         = local.tre_shared_service_tags

  # This is a temporary self-signed cert for CN=temp
  certificate {
    contents = filebase64("${path.module}/bootstrap.pfx")
    password = "0000000000"
  }

  certificate_policy {
    issuer_parameters {
      name = "Self"
    }
    key_properties {
      key_size   = 2048
      exportable = true
      key_type   = "RSA"
      reuse_key  = false
    }
    secret_properties {
      content_type = "application/x-pkcs12"
    }
  }

  # The certificate will get replaced with a real one, so we don't want Terraform to try and revert it.
  lifecycle {
    ignore_changes = all
  }

}

# pre-create in advance of the real password being created
# so if there is a deleted secret it will be recovered
#
resource "azurerm_key_vault_secret" "cert_password" {
  name         = local.password_name
  value        = "0000000000"
  key_vault_id = data.azurerm_key_vault.key_vault.id
  tags         = local.tre_shared_service_tags

  # The password will get replaced with a real one, so we don't want Terraform to try and revert it.
  lifecycle {
    ignore_changes = all
  }
}
