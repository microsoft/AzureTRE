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
  servicebus_diagnostic_categories_enabled = ["OperationalLogs", "VNetAndIPFilteringLogs", "RuntimeAuditLogs", "ApplicationMetricsLogs"]

  docker_registry_server = data.azurerm_container_registry.mgmt_acr.login_server

  # https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-firewall#allow-requests-from-the-azure-portal
  azure_portal_cosmos_ips = "104.42.195.92,40.76.54.131,52.176.6.30,52.169.50.45,52.187.184.26"

  # we define some zones in core despite not used by the core infra because
  # it's the easier way to make them available to other services in the system.
  private_dns_zone_names_non_core = toset([
    module.cloud_settings.private_links["privatelink.purview.azure.com"],
    module.cloud_settings.private_links["privatelink.purviewstudio.azure.com"],
    module.cloud_settings.private_links["privatelink.sql.azuresynapse.net"],
    module.cloud_settings.private_links["privatelink.dev.azuresynapse.net"],
    module.cloud_settings.private_links["privatelink.azuresynapse.net"],
    module.cloud_settings.private_links["privatelink.dfs.core.windows.net"],
    module.cloud_settings.private_links["privatelink.azurehealthcareapis.com"],
    module.cloud_settings.private_links["privatelink.dicom.azurehealthcareapis.com"],
    module.cloud_settings.private_links["privatelink.api.azureml.ms"],
    module.cloud_settings.private_links["privatelink.cert.api.azureml.ms"],
    module.cloud_settings.private_links["privatelink.notebooks.azure.net"],
    module.cloud_settings.private_links["privatelink.postgres.database.azure.com"],
    module.cloud_settings.private_links["privatelink.mysql.database.azure.com"],
    module.cloud_settings.private_links["privatelink.azuredatabricks.net"]
  ])

  service_bus_namespace_fqdn = regex("(?:(?P<scheme>[^:/?#]+):)?(?://(?P<fqdn>[^/?#:]*))?(?::(?P<port>[0-9]+))?(?P<path>[^?#]*)(?:\\?(?P<query>[^#]*))?(?:#(?P<fragment>.*))?", azurerm_servicebus_namespace.sb.endpoint).fqdn
}
