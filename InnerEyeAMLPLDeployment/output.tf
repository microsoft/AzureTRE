output "resourcegroup" {
    value = azurerm_resource_group.rg.name
}

output "location" {
    value = azurerm_machine_learning_workspace.ml.location
}

output "workspace_name" {
    value = azurerm_machine_learning_workspace.ml.name
}

output "computeinstance_name" {
    value = "${var.resource_name_prefix}ci"
}

output "computecluster_name" {
    value = "${var.resource_name_prefix}cl"
}

output "vnet_name" {
    value = azurerm_virtual_network.vnet.name
}

output "acr_name" {
    value = azurerm_container_registry.acr.name
}

output "subnet_name" {
    value = azurerm_subnet.default.name
}

output "admin_username" {
    value = var.username
}

output "admin_user_password" {
    value = var.password
}

output "inference_app_service" {
    value = azurerm_app_service.inference-app-service.name
}

output "inference_app_id" {
    value = azuread_application.inference-adapp.application_id
}

output "inference_password" {
    value = random_string.password.result
}

output "jumpbox_ip" {
    value = azurerm_public_ip.fwpip.ip_address
}

output "subscription_id" {
    value = data.azurerm_client_config.current.subscription_id
}

output "tenant_id" {
    value = data.azurerm_client_config.current.tenant_id
}