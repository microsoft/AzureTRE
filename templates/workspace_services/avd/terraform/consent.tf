data "azuread_service_principal" "windows_cloud_login" {
  count     = var.enable_sso_preconsent ? 1 : 0
  client_id = "270efc09-cd0d-444b-a71f-39af4910ec45"
}

resource "azuread_group" "avd_preconsent" {
  count                   = var.enable_sso_preconsent ? 1 : 0
  display_name            = "tre-avd-consent-${var.tre_resource_id}"
  description             = "Azure TRE AVD pre-consent ${var.workspace_id}/${var.tre_resource_id}"
  security_enabled        = true
  types                   = ["DynamicMembership"]
  prevent_duplicate_names = true

  dynamic_membership {
    enabled = true
    rule    = "(device.displayName -startsWith \"${local.session_host_name_prefix}\") -and (device.deviceTrustType -eq \"AzureAD\")"
  }
}

resource "msgraph_resource" "avd_preconsent_target" {
  count = var.enable_sso_preconsent ? 1 : 0
  url   = "servicePrincipals/${data.azuread_service_principal.windows_cloud_login[0].object_id}/remoteDesktopSecurityConfiguration/targetDeviceGroups"
  body = {
    id          = azuread_group.avd_preconsent[0].object_id
    displayName = azuread_group.avd_preconsent[0].display_name
  }
  response_export_values = {
    id = "id"
  }
}