resource "azapi_resource" "compute_instance" {
  type                      = "Microsoft.MachineLearningServices/workspaces/computes@2022-06-01-preview"
  name                      = local.aml_compute_instance_name
  location                  = data.azurerm_resource_group.ws.location
  parent_id                 = data.azurerm_machine_learning_workspace.workspace.id
  tags                      = local.tre_user_resources_tags
  schema_validation_enabled = false

  body = jsonencode({
    properties = {
      computeType = "ComputeInstance"
      properties = {
        vmSize                           = var.vm_size_sku
        computeInstanceAuthorizationType = "personal"
        enableNodePublicIp               = false
        personalComputeInstanceSettings = {
          assignedUser = {
            objectId = var.user_object_id
            tenantId = var.auth_tenant_id
          }
        }
        subnet = {
          id = data.azurerm_subnet.services.id
        }
      }
    }
  })
}
