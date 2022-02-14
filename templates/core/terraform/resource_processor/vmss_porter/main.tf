data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

data "template_file" "cloudconfig" {
  template = file("${path.module}/cloud-config.yaml")
  vars = {
    docker_registry_server                          = var.docker_registry_server
    terraform_state_container_name                  = var.terraform_state_container_name
    mgmt_resource_group_name                        = var.mgmt_resource_group_name
    mgmt_storage_account_name                       = var.mgmt_storage_account_name
    service_bus_deployment_status_update_queue      = var.service_bus_deployment_status_update_queue
    service_bus_resource_request_queue              = var.service_bus_resource_request_queue
    service_bus_namespace                           = "sb-${var.tre_id}.servicebus.windows.net"
    vmss_msi_id                                     = azurerm_user_assigned_identity.vmss_msi.client_id
    arm_subscription_id                             = data.azurerm_subscription.current.subscription_id
    arm_tenant_id                                   = data.azurerm_client_config.current.tenant_id
    resource_processor_vmss_porter_image_repository = var.resource_processor_vmss_porter_image_repository
    resource_processor_vmss_porter_image_tag        = local.version
    app_insights_connection_string                  = var.app_insights_connection_string
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

resource "azurerm_key_vault_secret" "resource_processor_vmss_password" {
  name         = "resource-processor-vmss-password"
  value        = random_password.password.result
  key_vault_id = var.keyvault_id
}

resource "azurerm_user_assigned_identity" "vmss_msi" {
  name                = "id-vmss-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_linux_virtual_machine_scale_set" "vm_linux" {

  name                = "vmss-rp-porter-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  upgrade_mode        = "Automatic"

  rolling_upgrade_policy {
    max_batch_instance_percent              = 100
    max_unhealthy_instance_percent          = 100
    max_unhealthy_upgraded_instance_percent = 10
    pause_time_between_batches              = "PT1M"

  }

  encryption_at_host_enabled = false

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.vmss_msi.id]
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
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}

resource "azurerm_role_assignment" "vmss_sb_sender" {
  scope                = var.service_bus_namespace_id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}

resource "azurerm_role_assignment" "vmss_sb_receiver" {
  scope                = var.service_bus_namespace_id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}

# add issue to look at reduced scope - needs to create and add resources to rgs
resource "azurerm_role_assignment" "subscription_owner" {
  # Below is a wordaround TF replacing this resource when using the data object.
  scope                = var.subscription_id != "" ? "/subscriptions/${var.subscription_id}" : data.azurerm_subscription.current.id
  role_definition_name = "Owner"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}
