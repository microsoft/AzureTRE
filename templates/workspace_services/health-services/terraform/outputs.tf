output "healthcare_workspace_id" {
  value = azurerm_healthcare_workspace.healthcare_workspace.id
}

output "fhir_url" {
  value = var.deploy_fhir ? "https://hs${local.service_resource_name_suffix}-fhir${local.service_resource_name_suffix}.fhir.azurehealthcareapis.com" : ""
}

output "dicom_url" {
  value = var.deploy_dicom ? "https://hs${local.service_resource_name_suffix}-dicom${local.service_resource_name_suffix}.dicom.azurehealthcareapis.com" : ""
}

output "workspace_address_space" {
  value = jsonencode(data.azurerm_virtual_network.ws.address_space)
}
