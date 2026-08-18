# Per-workspace airlock SAS signer.
#
# The airlock user-delegation SAS tokens are signed by whichever identity calls
# GetUserDelegationKey (the SAS "skoid"). To make the per-workspace ABAC condition
# on the shared global airlock storage account enforceable, each workspace has its
# own signer identity so that:
#   * the (principal, role, scope) role-assignment tuple is unique per workspace
#     (no RoleAssignmentExists 409 collision on the shared account), and
#   * a SAS leaked from one workspace cannot be replayed from another (the signer's
#     @Environment[privateEndpoints] condition denies access via a foreign PE).
#
# The signer is an Entra application/service principal. The shared core API managed
# identity is granted permission to federate as this signer (workload identity
# federation / "managed identity as FIC"), so it can mint SAS as the signer without
# any stored secret. The signer's client_id is surfaced as a workspace output and
# read at signing time.
#
# This requires TRE to be able to create Entra objects (register_aad_application).
# When that is not permitted, signing falls back to the shared core API identity.

locals {
  create_airlock_signer = var.register_aad_application
  aad_issuer            = "https://login.microsoftonline.com/${data.azuread_client_config.current.tenant_id}/v2.0"
}

resource "azuread_application" "airlock_signer" {
  count        = local.create_airlock_signer ? 1 : 0
  display_name = "airlock-signer-${var.short_workspace_id}"
  owners       = [data.azuread_client_config.current.object_id]

  lifecycle { ignore_changes = [owners] }
}

resource "azuread_service_principal" "airlock_signer" {
  count     = local.create_airlock_signer ? 1 : 0
  client_id = azuread_application.airlock_signer[0].client_id
  owners    = [data.azuread_client_config.current.object_id]

  feature_tags {
    enterprise = true
  }

  lifecycle { ignore_changes = [owners] }
}

# Allow the core API managed identity to federate as this workspace's signer.
resource "azuread_application_federated_identity_credential" "api" {
  count          = local.create_airlock_signer ? 1 : 0
  application_id = azuread_application.airlock_signer[0].id
  display_name   = "api-mi"
  description    = "Allows the core API managed identity to mint airlock SAS as this workspace's signer"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = local.aad_issuer
  subject        = data.azurerm_user_assigned_identity.api_id.principal_id
}
