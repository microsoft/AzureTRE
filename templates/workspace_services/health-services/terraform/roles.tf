
data "azurerm_key_vault_secret" "workspace_client_id" {
  name         = "workspace-client-id"
  key_vault_id = data.azurerm_key_vault.ws.id
}

data "external" "app_role_members" {
  program = ["bash", "${path.module}/get_app_role_members.sh"]

  query = {
    auth_client_id      = var.auth_client_id
    auth_client_secret  = var.auth_client_secret
    auth_tenant_id      = var.auth_tenant_id
    workspace_client_id = data.azurerm_key_vault_secret.workspace_client_id.value
  }
}

data "azurerm_role_definition" "azure_fhir_contributor" {
  name = "FHIR Data Contributor"
}

data "azurerm_role_definition" "azure_dicom_data_owner" {
  name = "DICOM Data Owner"
}

resource "azurerm_role_assignment" "app_role_members_fhir_contributor" {
  for_each           = !var.deploy_fhir || (data.external.app_role_members.result.principals == "") ? [] : toset(split("\n", data.external.app_role_members.result.principals))
  scope              = azurerm_healthcare_fhir_service.fhir[0].id
  role_definition_id = data.azurerm_role_definition.azure_fhir_contributor.id
  principal_id       = each.value
}

resource "azurerm_role_assignment" "app_role_members_dicom_data_owner" {
  for_each           = !var.deploy_dicom || (data.external.app_role_members.result.principals == "") ? [] : toset(split("\n", data.external.app_role_members.result.principals))
  scope              = azurerm_healthcare_dicom_service.dicom[0].id
  role_definition_id = data.azurerm_role_definition.azure_dicom_data_owner.id
  principal_id       = each.value
}
