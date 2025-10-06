locals {
  myip = var.public_deployment_ip_address != "" ? var.public_deployment_ip_address : chomp(data.http.myip[0].response_body)
  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }
  api_diagnostic_categories_enabled = [
    "AppServiceHTTPLogs", "AppServiceConsoleLogs", "AppServiceAppLogs", "AppServiceFileAuditLogs",
    "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs", "AppServiceAntivirusScanAuditLogs"
  ]
  docker_registry_server = "${var.acr_name}.azurecr.io"

  # https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-firewall#allow-requests-from-the-azure-portal
  azure_portal_cosmos_ips = "104.42.195.92,40.76.54.131,52.176.6.30,52.169.50.45,52.187.184.26"

  # we define some zones in core despite not used by the core infra because
  # it's the easier way to make them available to other services in the system.
  private_dns_zone_names_non_core = toset([
    "privatelink.purview.azure.com",
    "privatelink.purviewstudio.azure.com",
    "privatelink.database.windows.net",
    "privatelink.sql.azuresynapse.net",
    "privatelink.dev.azuresynapse.net",
    "privatelink.azuresynapse.net",
    "privatelink.dfs.core.windows.net",
    "privatelink.azurehealthcareapis.com",
    "privatelink.dicom.azurehealthcareapis.com",
    "privatelink.api.azureml.ms",
    "privatelink.cert.api.azureml.ms",
    "privatelink.notebooks.azure.net",
    "privatelink.postgres.database.azure.com",
    "nexus-${var.tre_id}.${var.location}.cloudapp.azure.com",
    "privatelink.mysql.database.azure.com",
    "privatelink.azuredatabricks.net"
  ])

  storage_table_scope      = "/subscriptions/${data.azurerm_subscription.current.subscription_id}/resourceGroups/rg-${var.tre_id}/providers/Microsoft.Storage/storageAccounts/stg${var.tre_id}/tableServices/default/tables"
  core_keyvault_name       = "kv-${var.tre_id}"
  core_resource_group_name = "rg-${var.tre_id}"
  env_rules = [
    { match = "cprdprod", val = "p" },
    { match = "cprdstaging", val = "s" },
    { match = "cprdtest", val = "t" },
    { match = "cprddev", val = "d" },
  ]
  matches = [
    for r in local.env_rules :
    r.val if(r.match == var.tre_id) || endswith(var.tre_id, r.match)
  ]
  arm_client_id     = "arm-client-id"
  arm_client_secret = "arm-client-secret"
  data_environment  = length(local.matches) > 0 ? local.matches[0] : "?"
}
