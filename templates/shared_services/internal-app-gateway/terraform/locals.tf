locals {
  path_map_name                  = "upm-dynamic-inbound"
  secure_frontend_port_name      = "feport-secure"
  frontend_ip_configuration_name = "feip-private"
  secure_listener_name           = "httplstn-secure"
  request_routing_rule_name      = "rqrt-dynamic"
  certificate_name               = "cert"
  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }

  core_resource_group_name = "rg-${var.tre_id}"

  default_route_fqdn = "stweb${var.tre_id}.z1.web.core.windows.net"

  backend_count_per_agw         = 100
  dynamic_backend_settings_name = "bes-generic-443-with-host"
  dynamic_rewrite_set           = "rs-dynamic"
  dynamic_backends              = jsondecode(base64decode(var.backend_collection_b64))
  dynamic_backends_chunked      = chunklist(coalescelist(local.dynamic_backends, local.first_backend), local.backend_count_per_agw)
  first_backend = [
    {
      name = "first"
      fqdn = local.default_route_fqdn
    }
  ]

  url_parts_pattern = "(?:(?P<scheme>[^:/?#]+):)?(?://(?P<fqdn>[^/?#:]*))?(?::(?P<port>[0-9]+))?(?P<path>[^?#]*)(?:\\?(?P<query>[^#]*))?(?:#(?P<fragment>.*))?"

  internal_agw_ip_step            = 1
  internal_agw_ip_start           = 5
  internal_agw_ips                = [for i in range(local.internal_agw_ip_start, local.internal_agw_ip_start + var.internal_agw_count * local.internal_agw_ip_step, local.internal_agw_ip_step) : cidrhost(data.azurerm_subnet.agw_int.address_prefixes[0], i)]
  internal_agw_backend_url_prefix = "i"
  keyvault_cert_prefix            = "cert"

  appgateway_diagnostic_categories_enabled = ["ApplicationGatewayAccessLog", "ApplicationGatewayPerformanceLog", "ApplicationGatewayFirewallLog"]
}
