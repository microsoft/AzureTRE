# Per-workspace signers prevent role collisions and bind SAS access to each private endpoint.

locals {
  aad_issuer = "${module.terraform_azurerm_environment_configuration.active_directory_endpoint}/${data.azuread_client_config.current.tenant_id}/v2.0"
}

resource "azuread_application" "airlock_signer" {
  display_name = "airlock-signer-${var.short_workspace_id}"
  owners       = [data.azuread_client_config.current.object_id]

  lifecycle { ignore_changes = [owners] }
}

resource "azuread_service_principal" "airlock_signer" {
  client_id = azuread_application.airlock_signer.client_id
  owners    = [data.azuread_client_config.current.object_id]

  feature_tags {
    enterprise = true
  }

  lifecycle { ignore_changes = [owners] }
}

resource "azuread_application_federated_identity_credential" "api" {
  application_id = azuread_application.airlock_signer.id
  display_name   = "api-mi"
  description    = "Allows the core API managed identity to mint airlock SAS as this workspace's signer"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = local.aad_issuer
  subject        = data.azurerm_user_assigned_identity.api_id.principal_id
}
