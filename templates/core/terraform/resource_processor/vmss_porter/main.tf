data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

data "template_file" "cloudconfig" {
  template = file("${path.module}/cloud-config.yaml")
  vars = {
    resource_processor_vmss_porter_image_repository = var.resource_processor_vmss_porter_image_repository
    resource_processor_vmss_porter_image_tag        = var.resource_processor_vmss_porter_image_tag
    docker_registry_server                          = var.docker_registry_server
    service_bus_connection_string                   = var.service_bus_connection_string
    service_bus_resource_request_queue              = var.service_bus_resource_request_queue
    service_bus_deployment_status_update_queue      = var.service_bus_deployment_status_update_queue
    arm_tenant_id                                   = data.azurerm_client_config.current.tenant_id
    arm_subscription_id                             = data.azurerm_subscription.current.subscription_id
    resource_processor_client_id                    = var.resource_processor_client_id
    resource_processor_client_secret                = var.resource_processor_client_secret
    mgmt_storage_account_name                       = var.mgmt_storage_account_name
    mgmt_resource_group_name                        = var.mgmt_resource_group_name
    terraform_state_container_name                  = var.terraform_state_container_name
    app_insights_connection_string                  = var.app_insights_connection_string
    acr_pull_identity                               = azurerm_user_assigned_identity.acr_pull.id
  }
}

data "template_cloudinit_config" "config" {
  gzip          = true
  base64_encode = true

  part {
    content_type = "text/cloud-config"
    content      = data.template_file.cloudconfig.rendered
  }
}

resource "random_password" "password" {
  length           = 16
  special          = true
  override_special = "_%@"
}

resource "azurerm_user_assigned_identity" "acr_pull" {
  name                = "acr_pull"
  location            = var.location
  resource_group_name = var.resource_group_name
  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_linux_virtual_machine_scale_set" "vm_linux" {

  name                       = "vmss-rp-porter-${var.tre_id}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  upgrade_mode               = "Automatic"

  rolling_upgrade_policy {
    max_batch_instance_percent = 100
    max_unhealthy_instance_percent = 100
    max_unhealthy_upgraded_instance_percent = 10
    pause_time_between_batches = "PT1M"

  }

  encryption_at_host_enabled = false

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.acr_pull.id]
  }


  sku       = "Standard_B2s"
  instances = 1

  admin_username                  = "adminuser"
  disable_password_authentication = false

  admin_password = random_password.password.result
  custom_data    = data.template_cloudinit_config.config.rendered

  source_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "18.04-LTS"
    version   = "latest"
  }

  os_disk {
    storage_account_type = "Standard_LRS"
    caching              = "ReadWrite"
  }

  network_interface {
    name    = "nic1"
    primary = true

    ip_configuration {
      name      = "internal"
      primary   = true
      subnet_id = var.resource_processor_subnet_id
    }
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "vmss_acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.acr_pull.principal_id
}
