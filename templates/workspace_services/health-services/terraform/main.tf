resource "azurerm_healthcare_workspace" "healthcare_workspace" {
  name                = "hs${local.service_resource_name_suffix}"
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location
  tags                = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_healthcare_fhir_service" "fhir" {
  count               = var.deploy_fhir ? 1 : 0
  name                = "fhir${local.service_resource_name_suffix}"
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location
  workspace_id        = azurerm_healthcare_workspace.healthcare_workspace.id
  kind                = "fhir-${var.fhir_kind}"
  tags                = local.workspace_service_tags

  authentication {
    authority = local.authority
    audience  = "https://hs${local.service_resource_name_suffix}-fhir${local.service_resource_name_suffix}.fhir.azurehealthcareapis.com"
  }

  identity {
    type = "SystemAssigned"
  }


  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_healthcare_dicom_service" "dicom" {
  count        = var.deploy_dicom ? 1 : 0
  name         = "dicom${local.service_resource_name_suffix}"
  workspace_id = azurerm_healthcare_workspace.healthcare_workspace.id
  location     = data.azurerm_resource_group.ws.location
  tags         = local.workspace_service_tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "health_services_private_endpoint" {
  name                = "pe-${azurerm_healthcare_workspace.healthcare_workspace.name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.health.id, data.azurerm_private_dns_zone.dicom.id]
  }

  private_service_connection {
    private_connection_resource_id = azurerm_healthcare_workspace.healthcare_workspace.id
    name                           = "psc-${azurerm_healthcare_workspace.healthcare_workspace.name}"
    subresource_names              = ["healthcareworkspace"]
    is_manual_connection           = false
  }

  depends_on = [
    azurerm_healthcare_fhir_service.fhir,
    azurerm_healthcare_dicom_service.dicom
  ]

  lifecycle { ignore_changes = [tags] }
}
