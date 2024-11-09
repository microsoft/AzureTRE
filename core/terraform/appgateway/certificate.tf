resource "azurerm_role_assignment" "keyvault_appgw_role" {
  scope                = var.keyvault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.agw_id.principal_id // id-agw-<TRE_ID>
}

resource "azurerm_key_vault_certificate" "tlscert" {
  name         = "letsencrypt"
  key_vault_id = var.keyvault_id
  tags         = local.tre_core_tags

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

    x509_certificate_properties {
      # Server Authentication = 1.3.6.1.5.5.7.3.1
      # Client Authentication = 1.3.6.1.5.5.7.3.2
      extended_key_usage = ["1.3.6.1.5.5.7.3.1"]

      key_usage = [
        "cRLSign",
        "dataEncipherment",
        "digitalSignature",
        "keyAgreement",
        "keyCertSign",
        "keyEncipherment",
      ]

      subject = "CN=${azurerm_public_ip.appgwpip.fqdn}"

      subject_alternative_names {
        dns_names = [azurerm_public_ip.appgwpip.fqdn]
      }

      validity_in_months = 12
    }
  }

  # The certificate will get replaced with a real one, so we don't want Terrafomr to try and revert it.
  lifecycle {
    ignore_changes = all
  }
}
