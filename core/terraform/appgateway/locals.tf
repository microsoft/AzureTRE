locals {
  staticweb_storage_name = lower(replace("stweb${var.tre_id}", "-", ""))

  staticweb_backend_pool_name = "beap-staticweb"
  api_backend_pool_name       = "beap-api"
  app_path_map_name           = "upm-application"
  redirect_path_map_name      = "upm-redirect"

  # Airlock core storage backend (only core storage needs public App Gateway access)
  # Workspace storage is accessed internally via private endpoints
  airlock_core_backend_pool_name = "beap-airlock-core"
  airlock_core_http_setting_name = "be-htst-airlock-core"
  airlock_core_probe_name        = "hp-airlock-core"

  insecure_frontend_port_name = "feport-insecure"
  secure_frontend_port_name   = "feport-secure"

  frontend_ip_configuration_name = "feip-public"

  api_http_setting_name       = "be-htst-api"
  staticweb_http_setting_name = "be-htst-staticweb"

  api_probe_name = "hp-api"

  insecure_listener_name = "httplstn-insecure"
  secure_listener_name   = "httplstn-secure"

  redirect_request_routing_rule_name = "rqrt-redirect"
  request_routing_rule_name          = "rqrt-application"
  redirect_configuration_name        = "rdrcfg-tosecure"

  certificate_name = "cert-primary"
  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }

  appgateway_diagnostic_categories_enabled = ["ApplicationGatewayAccessLog", "ApplicationGatewayPerformanceLog", "ApplicationGatewayFirewallLog"]
}
