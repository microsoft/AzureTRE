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

  # Terraform creates the services after the private endpoint and deletes them before it.
  depends_on = [azurerm_private_endpoint.health_services_private_endpoint]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_healthcare_dicom_service" "dicom" {
  count        = var.deploy_dicom ? 1 : 0
  name         = "dicom${local.service_resource_name_suffix}"
  workspace_id = azurerm_healthcare_workspace.healthcare_workspace.id
  location     = data.azurerm_resource_group.ws.location
  tags         = local.workspace_service_tags

  # The provider default turns on public network access.
  public_network_access_enabled = false

  identity {
    type = "SystemAssigned"
  }

  # Terraform creates the services after the private endpoint and deletes them before it.
  depends_on = [azurerm_private_endpoint.health_services_private_endpoint]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "health_services_private_endpoint" {
  name                = "pe-${azurerm_healthcare_workspace.healthcare_workspace.name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_healthcare_workspace.healthcare_workspace.id
    name                           = "psc-${azurerm_healthcare_workspace.healthcare_workspace.name}"
    subresource_names              = ["healthcareworkspace"]
    is_manual_connection           = false
  }

  # The DNS zone group is a separate resource. The provider changes a zone group in this
  # resource only together with the whole endpoint.
  lifecycle { ignore_changes = [tags, private_dns_zone_group] }
}

# Before version 0.3.9, the endpoint resource created the DNS zone group. This removes
# that group once, so that the resource below can create a group with the same name.
resource "azapi_resource_action" "remove_endpoint_dns_zone_group" {
  type        = "Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01"
  resource_id = "${azurerm_private_endpoint.health_services_private_endpoint.id}/privateDnsZoneGroups/private-dns-zone-group"
  method      = "DELETE"

  retry = {
    error_message_regex = ["AnotherOperationInProgress"]
  }
}

# Azure writes the private DNS records of a zone when the group gets that zone. Azure
# links a new service to the endpoint after the service create returns. A change to the
# group during this time gets HTTP 409, so the provider tries again.
resource "azapi_resource" "health_services_dns_zone_group" {
  type      = "Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01"
  name      = "private-dns-zone-group"
  parent_id = azurerm_private_endpoint.health_services_private_endpoint.id

  body = {
    properties = {
      privateDnsZoneConfigs = concat(
        [{ name = "health", properties = { privateDnsZoneId = data.azurerm_private_dns_zone.health.id } }],
        var.deploy_dicom ? [{ name = "dicom", properties = { privateDnsZoneId = data.azurerm_private_dns_zone.dicom.id } }] : []
      )
    }
  }

  retry = {
    error_message_regex = ["AnotherOperationInProgress"]
  }

  depends_on = [
    azapi_resource_action.remove_endpoint_dns_zone_group,
    azurerm_healthcare_fhir_service.fhir,
    azurerm_healthcare_dicom_service.dicom
  ]
}
