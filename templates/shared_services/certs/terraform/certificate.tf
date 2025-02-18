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
    contents = "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"
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
