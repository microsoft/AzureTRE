resource "azurerm_resource_group_template_deployment" "smtp_api_connection" {
  name                = "smtp-api-connection"
  resource_group_name = data.azurerm_resource_group.core.name

  template_content = data.local_file.smtp_api_connection.content

  parameters_content = jsonencode({
    "serverAddress" = {
      value = var.smtp_server_address
    },
    "userName" = {
      value = var.smtp_username
    },
    "password" = {
      value = var.smtp_password
    }
  })

  deployment_mode = "Incremental"
}

resource "azurerm_resource_group_template_deployment" "smtp_api_connection_access_policy" {
  name                = "smtp-api-connection-access-policy"
  resource_group_name = data.azurerm_resource_group.core.name

  template_content = data.local_file.smtp_access_policy.content

  parameters_content = jsonencode({
    "servicePrincipalId" = {
      value = azurerm_logic_app_standard.logic_app.identity.0.principal_id
    },
    "servicePrincipalTenantId" = {
      value = azurerm_logic_app_standard.logic_app.identity.0.tenant_id
    }
  })

  deployment_mode = "Incremental"
  tags            = local.tre_shared_service_tags
  lifecycle { ignore_changes = [tags] }
}
