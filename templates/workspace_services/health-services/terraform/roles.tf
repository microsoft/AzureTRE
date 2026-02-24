# Role assignments for workspace researchers group
resource "azurerm_role_assignment" "researchers_fhir_contributor" {
  count              = var.deploy_fhir && var.workspace_researchers_group_id != "" ? 1 : 0
  scope              = azurerm_healthcare_fhir_service.fhir[0].id
  role_definition_id = data.azurerm_role_definition.azure_fhir_contributor.id
  principal_id       = var.workspace_researchers_group_id
}

resource "azurerm_role_assignment" "researchers_dicom_data_owner" {
  count              = var.deploy_dicom && var.workspace_researchers_group_id != "" ? 1 : 0
  scope              = azurerm_healthcare_dicom_service.dicom[0].id
  role_definition_id = data.azurerm_role_definition.azure_dicom_data_owner.id
  principal_id       = var.workspace_researchers_group_id
}

# Role assignments for workspace owners group
resource "azurerm_role_assignment" "owners_fhir_contributor" {
  count              = var.deploy_fhir && var.workspace_owners_group_id != "" ? 1 : 0
  scope              = azurerm_healthcare_fhir_service.fhir[0].id
  role_definition_id = data.azurerm_role_definition.azure_fhir_contributor.id
  principal_id       = var.workspace_owners_group_id
}

resource "azurerm_role_assignment" "owners_dicom_data_owner" {
  count              = var.deploy_dicom && var.workspace_owners_group_id != "" ? 1 : 0
  scope              = azurerm_healthcare_dicom_service.dicom[0].id
  role_definition_id = data.azurerm_role_definition.azure_dicom_data_owner.id
  principal_id       = var.workspace_owners_group_id
}

data "azurerm_role_definition" "azure_fhir_contributor" {
  name = "FHIR Data Contributor"
}

data "azurerm_role_definition" "azure_dicom_data_owner" {
  name = "DICOM Data Owner"
}
