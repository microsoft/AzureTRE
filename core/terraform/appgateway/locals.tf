locals {
  staticweb_storage_name = lower(replace("stweb${var.tre_id}", "-", ""))

  staticweb_backend_pool_name = "beap-staticweb"
  api_backend_pool_name       = "beap-api"
  app_path_map_name           = "upm-application"
  redirect_path_map_name      = "upm-redirect"

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

  internal_agw_backend_pool_name_prefix = "beap-internal"
  internal_agw_backend_url_prefix       = "i"
  internal_agw_http_setting_name        = "be-htst-internal-agw"
  internal_agw_ruleset_name             = "rs-internal-agw"
  internal_agw_ip_step                  = 1
  internal_agw_ip_start                 = 5
  internal_agw_ips                      = [for i in range(local.internal_agw_ip_start, local.internal_agw_ip_start + var.internal_agw_count * local.internal_agw_ip_step, local.internal_agw_ip_step) : cidrhost(var.internal_agw_subnet_cidr, i)]
  internal_agw_ips_max                  = [for i in range(local.internal_agw_ip_start, local.internal_agw_ip_start + 10 * local.internal_agw_ip_step, local.internal_agw_ip_step) : cidrhost(var.internal_agw_subnet_cidr, i)]
  keyvault_cert_prefix                  = "cert"
  ca_common_name                        = "${var.tre_id}-ca"
  internal_agw_ca_certificate_name      = "cert-ca"
}
