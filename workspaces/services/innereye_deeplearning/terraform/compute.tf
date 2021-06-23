data "local_file" "deploypl_aml_compute" {
  filename = "${path.module}/nopipcompute/deploypl_aml_compute.json"
}

data "local_file" "deploypl_compute_instance" {
  filename = "${path.module}/nopipcompute/deploypl_compute_instance.json"
}

# open required NSG rules SECURITY ISSUE
resource "azurerm_network_security_rule" "aml-compute-storage-access" {
  access                      = "Allow"
  destination_address_prefix  = "Storage.${data.azurerm_resource_group.ws.location}"
  destination_port_range      = "445"
  direction                   = "Outbound"
  name                        = "allow-aml-compute-storage-access"
  network_security_group_name = data.azurerm_network_security_group.ws.name
  priority                    = 1000
  protocol                    = "TCP"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_address_prefix       = "VirtualNetwork"
  source_port_range           = "*"
}

# need to add existing VNET
resource "azurerm_resource_group_template_deployment" "deploy_aml_compute" {
  name                = "dpl-${local.service_resource_name_suffix}_deploy_aml_compute"
  resource_group_name = data.azurerm_resource_group.ws.name

  template_content  = data.local_file.deploypl_aml_compute.content


  # these key-value pairs are passed into the ARM Template's `parameters` block
  parameters_content = jsonencode({
    "vnet_name" = {
      value = data.azurerm_virtual_network.ws.name
    },
    "location" = {
      value = data.azurerm_resource_group.ws.location
    },
    "workspace_name" = {
      value = var.azureml_workspace_name
    },
    "cluster_name" = {
      value = "cp-${local.aml_compute_id}"
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


resource "azurerm_resource_group_template_deployment" "deploy_compute_instance" {
  name                = "dpl-${local.service_resource_name_suffix}-deploy_compute_instance"
  resource_group_name = data.azurerm_resource_group.ws.name

  template_content  = data.local_file.deploypl_compute_instance.content

  # these key-value pairs are passed into the ARM Template's `parameters` block
  parameters_content = jsonencode({


    "vnet_name" = {
      "value" = data.azurerm_virtual_network.ws.name
    },
    "location" = {
      "value" = data.azurerm_resource_group.ws.location
    },
    "workspace_name" = {
      "value" = var.azureml_workspace_name
    },
    "instance_name" = {
      "value" = "ci-${local.aml_compute_id}"
    },
    "subnet_name" = {
      "value" = data.azurerm_subnet.services.name
    },
    "vm_size_sku" = {
      "value" = "Standard_D4_v2"

    }
  })

  deployment_mode = "Incremental"
}
