locals {
  myip = var.public_deployment_ip_address != "" ? var.public_deployment_ip_address : chomp(data.http.myip[0].response_body)
  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }

  api_diagnostic_categories_enabled = [
    "AppServiceHTTPLogs", "AppServiceConsoleLogs", "AppServiceAppLogs",
    "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs", "AppServiceAntivirusScanAuditLogs"
  ]
  servicebus_diagnostic_categories_enabled = ["OperationalLogs", "VNetAndIPFilteringLogs", "RuntimeAuditLogs", "ApplicationMetricsLogs"]

  docker_registry_server = data.azurerm_container_registry.mgmt_acr.login_server

  mgmt_storage_account_id = data.azurerm_storage_account.mgmt_storage.id

  # https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-firewall#allow-requests-from-the-azure-portal

  azure_portal_cosmos_ips_list = [
    "13.91.105.215",
    "4.210.172.107",
    "13.88.56.148",
    "40.91.218.243"
  ]

  cosmos_ip_filter_set = toset(
    var.enable_local_debugging
    ? concat(local.azure_portal_cosmos_ips_list, [local.myip])
    : []
  )

  # we define some zones in core despite not used by the core infra because
  # it's the easier way to make them available to other services in the system.
  private_dns_zone_names_non_core = toset([
    "privatelink.purview.azure.com",
    "privatelink.purviewstudio.azure.com",
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
    "privatelink.mysql.database.azure.com",
    "privatelink.database.windows.net",
    "privatelink.azuredatabricks.net",
    "privatelink.openai.azure.com",
    "privatelink.cognitiveservices.azure.com"
  ])

  # The followig regex extracts different parts of the service bus endpoint: scheme, fqdn, port, path, query and fragment. This allows us to extract the needed fqdn part.
  service_bus_namespace_fqdn = regex("(?:(?P<scheme>[^:/?#]+):)?(?://(?P<fqdn>[^/?#:]*))?(?::(?P<port>[0-9]+))?(?P<path>[^?#]*)(?:\\?(?P<query>[^#]*))?(?:#(?P<fragment>.*))?", azurerm_servicebus_namespace.sb.endpoint).fqdn

  # The key store for encryption keys could either be external or created by terraform
  key_store_id = var.enable_cmk_encryption ? (var.external_key_store_id != null ? var.external_key_store_id : data.azurerm_key_vault.encryption_kv[0].id) : ""

  cmk_name                 = "tre-encryption-${var.tre_id}"
  encryption_identity_name = "id-encryption-${var.tre_id}"

  # key vault variables
  kv_name                          = "kv-${var.tre_id}"
  kv_public_network_access_enabled = true
  kv_network_default_action        = var.enable_local_debugging ? "Allow" : "Deny"
  kv_network_bypass                = "AzureServices"
}
