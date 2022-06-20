data "local_file" "deploypl_compute_instance" {
  filename = "${path.module}/deploypl_compute_instance.json"
}

resource "azurerm_resource_group_template_deployment" "deploy_compute_instance" {
  name                = "dpl-${local.user_resource_name_suffix}"
  resource_group_name = data.azurerm_resource_group.ws.name
  tags                = local.tre_user_resources_tags
  template_content    = data.local_file.deploypl_compute_instance.content

  # these key-value pairs are passed into the ARM Template's `parameters` block
  parameters_content = jsonencode({


    "vnet_name" = {
      "value" = data.azurerm_virtual_network.ws.name
    },
    "location" = {
      "value" = data.azurerm_resource_group.ws.location
    },
    "workspace_name" = {
      "value" = local.aml_workspace_name
    },
    "instance_name" = {
      "value" = local.aml_compute_instance_name
    },
    "subnet_name" = {
      "value" = data.azurerm_subnet.services.name
    },
    "vm_size_sku" = {
      "value" = var.vm_size_sku
    },
    "user_object_id" = {
      "value" = var.user_object_id
    },
    "tenant_id" = {
      "value" = var.auth_tenant_id
    }
  })

  deployment_mode = "Incremental"
}
