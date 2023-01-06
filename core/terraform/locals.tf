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
}
