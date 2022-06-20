data "local_file" "deploypl_compute_cluster" {
  filename = "${path.module}/nopipcompute/deploypl_compute_cluster.json"
}

# need to add existing VNET
resource "azurerm_resource_group_template_deployment" "deploy_compute_cluster" {
  name                = "dpl-${local.service_resource_name_suffix}_deploy_compute_cluster"
  resource_group_name = data.azurerm_resource_group.ws.name
  tags                = local.tre_workspace_service_tags

  template_content = data.local_file.deploypl_compute_cluster.content


  # these key-value pairs are passed into the ARM Template's `parameters` block
  parameters_content = jsonencode({
    "vnet_name" = {
      value = data.azurerm_virtual_network.ws.name
    },
    "location" = {
      value = data.azurerm_resource_group.ws.location
    },
    "workspace_name" = {
      value = local.aml_workspace_name
    },
    "cluster_name" = {
      value = local.aml_compute_cluster_name
    },
    "subnet_name" = {
      value = data.azurerm_subnet.services.name
    },
    "admin_username" = {
      value = "azureuser"
    },
    "admin_user_password" = {
      "value" = "DONOTMERGE"
    },
    "vm_size_sku" = {
      "value" = "Standard_D4_v2"
    },
    "min_node_count" = {
      "value" = 0
    },
    "max_node_count" = {
      "value" = 1
    }
  })

  deployment_mode = "Incremental"
}

data "azurerm_container_registry" "aml" {
  name                = local.azureml_acr_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

resource "azurerm_role_assignment" "compute_cluster_acr_pull" {
  scope                = data.azurerm_container_registry.aml.id
  role_definition_name = "AcrPull"
  principal_id         = jsondecode(azurerm_resource_group_template_deployment.deploy_compute_cluster.output_content).cluster_principal_id.value
}
