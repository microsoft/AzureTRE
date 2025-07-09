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

  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }

  core_resource_group_name = "rg-${var.tre_id}"

  dynamic_backend_settings_name = "bes-generic-443-with-host"
  dynamic_rewrite_set           = "rs-non-core"
  dynamic_backends              = jsondecode(base64decode(var.backend_collection_b64))

  url_parts_pattern = "(?:(?P<scheme>[^:/?#]+):)?(?://(?P<fqdn>[^/?#:]*))?(?::(?P<port>[0-9]+))?(?P<path>[^?#]*)(?:\\?(?P<query>[^#]*))?(?:#(?P<fragment>.*))?"
}
