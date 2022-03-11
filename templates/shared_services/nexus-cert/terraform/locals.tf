locals {
  staticweb_storage_name = lower(replace("stwebnexus${var.tre_id}", "-", ""))

  core_resource_group_name = "rg-${var.tre_id}"

  staticweb_backend_pool_name = "beap-nexuscret-staticweb"
  app_path_map_name           = "upm-nexuscert"
  redirect_path_map_name      = "upm-nexuscert-redirect"

  insecure_frontend_port_name = "feport-nexuscert-insecure"
  secure_frontend_port_name   = "feport-nexuscert-secure"

  frontend_ip_configuration_name = "feip-nexuscert-public"

  staticweb_http_setting_name = "be-htst-nexuscert-staticweb"

  insecure_listener_name = "httplstn-nexuscert-insecure"
  secure_listener_name   = "httplstn-nexuscert-secure"

  redirect_request_routing_rule_name = "rqrt-nexuscert-redirect"
  request_routing_rule_name          = "rqrt-nexuscert-application"
  redirect_configuration_name        = "rdrcfg-nexuscert-tosecure"

  certificate_name = "cert-nexus-primary"
}
