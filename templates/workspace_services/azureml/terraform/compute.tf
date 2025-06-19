resource "random_password" "password" {
  length           = 16
  lower            = true
  min_lower        = 1
  upper            = true
  min_upper        = 1
  numeric          = true
  min_numeric      = 1
  special          = true
  min_special      = 1
  override_special = "_%@"
}

resource "azurerm_key_vault_secret" "aml_password" {
  name         = "cp-${local.short_service_id}"
  value        = random_password.password.result
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}


resource "azapi_resource" "compute_cluster" {
  type      = "Microsoft.MachineLearningServices/workspaces/computes@2022-10-01"
  name      = "cp-${local.short_service_id}"
  location  = data.azurerm_resource_group.ws.location
  parent_id = azapi_resource.aml_workspace.output.id
  tags      = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = {
      computeLocation  = data.azurerm_resource_group.ws.location
      description      = "Default Compute Cluster"
      disableLocalAuth = true
      computeType      = "AmlCompute"
      properties = {
        enableNodePublicIp          = false
        isolatedNetwork             = false # isolatedNetwork = true for internal MS usage only
        osType                      = "Linux"
        remoteLoginPortPublicAccess = "Disabled"
        scaleSettings = {
          maxNodeCount                = 1
          minNodeCount                = 0
          nodeIdleTimeBeforeScaleDown = "PT10M"
        }
        subnet = {
          id = azurerm_subnet.aml.id
        }
        vmPriority = "Dedicated"
        vmSize     = "Standard_DS2_v2"
      }
    }
  }

  depends_on = [
    azurerm_private_endpoint.mlpe,
    azurerm_private_endpoint.blobpe,
    azurerm_private_endpoint.filepe
  ]

  response_export_values = ["*"]

}

resource "azapi_update_resource" "set_image_build_compute" {
  type      = "Microsoft.MachineLearningServices/workspaces@2022-10-01"
  name      = azapi_resource.aml_workspace.output.name
  parent_id = data.azurerm_resource_group.ws.id

  body = {
    properties = {
      imageBuildCompute = azapi_resource.compute_cluster.output.name
    }
  }

  depends_on = [
    azapi_resource.compute_cluster
  ]
}
