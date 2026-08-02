# Using AzApi due to https://github.com/hashicorp/terraform-provider-azurerm/issues/15362
resource "azapi_resource" "compute_instance" {
  type                      = "Microsoft.MachineLearningServices/workspaces/computes@2022-06-01-preview"
  name                      = local.aml_compute_instance_name
  location                  = data.azurerm_resource_group.ws.location
  parent_id                 = data.azurerm_machine_learning_workspace.workspace.id
  tags                      = local.tre_user_resources_tags
  schema_validation_enabled = false

  body = {
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
          id = data.azurerm_subnet.aml.id
        }
      }
    }
  }

  lifecycle { ignore_changes = [tags] }

  depends_on = [
    azurerm_role_assignment.user_storage_blob_data_contributor,
    azurerm_role_assignment.user_storage_file_data_contributor
  ]
}

resource "azurerm_role_assignment" "user_storage_blob_data_contributor" {
  scope              = data.azurerm_storage_account.aml.id
  role_definition_id = data.azurerm_role_definition.storage_blob_data_contributor.id
  principal_id       = var.user_object_id
}

resource "azurerm_role_assignment" "user_storage_file_data_contributor" {
  scope              = data.azurerm_storage_account.aml.id
  role_definition_id = data.azurerm_role_definition.storage_file_data_contributor.id
  principal_id       = var.user_object_id
}
