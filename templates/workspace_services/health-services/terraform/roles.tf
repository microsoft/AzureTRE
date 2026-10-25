# Azure returns the role definition ID with the subscription. An ID without it in the
# configuration replaces each role assignment at each update, so these use the role name.

# Role assignments for workspace researchers group
resource "azurerm_role_assignment" "researchers_fhir_contributor" {
  count                = var.deploy_fhir && var.workspace_researchers_group_id != "" ? 1 : 0
  scope                = azurerm_healthcare_fhir_service.fhir[0].id
  role_definition_name = "FHIR Data Contributor"
  principal_id         = var.workspace_researchers_group_id
}

resource "azurerm_role_assignment" "researchers_dicom_data_owner" {
  count                = var.deploy_dicom && var.workspace_researchers_group_id != "" ? 1 : 0
  scope                = azurerm_healthcare_dicom_service.dicom[0].id
  role_definition_name = "DICOM Data Owner"
  principal_id         = var.workspace_researchers_group_id
}

# Role assignments for workspace owners group
resource "azurerm_role_assignment" "owners_fhir_contributor" {
  count                = var.deploy_fhir && var.workspace_owners_group_id != "" ? 1 : 0
  scope                = azurerm_healthcare_fhir_service.fhir[0].id
  role_definition_name = "FHIR Data Contributor"
  principal_id         = var.workspace_owners_group_id
}

resource "azurerm_role_assignment" "owners_dicom_data_owner" {
  count                = var.deploy_dicom && var.workspace_owners_group_id != "" ? 1 : 0
  scope                = azurerm_healthcare_dicom_service.dicom[0].id
  role_definition_name = "DICOM Data Owner"
  principal_id         = var.workspace_owners_group_id
}
