locals {
  staticweb_storage_name = lower(replace("stweb${var.tre_id}", "-", ""))

  staticweb_index_file_content = "<!DOCTYPE html><html lang=\"en\" xmlns=\"http://www.w3.org/1999/xhtml\"><head><meta charset=\"utf-8\"/><title></title></head><body></body></html>"

  staticweb_backend_pool_name = "beap-staticweb"
  api_backend_pool_name       = "beap-api"
  nexus_backend_pool_name     = "beap-nexus"
  gitea_backend_pool_name     = "beap-gitea"
  app_path_map_name           = "upm-application"
  redirect_path_map_name      = "upm-redirect"

  insecure_frontend_port_name = "feport-insecure"
  secure_frontend_port_name   = "feport-secure"

  frontend_ip_configuration_name = "feip-public"

  api_http_setting_name       = "be-htst-api"
  staticweb_http_setting_name = "be-htst-staticweb"
  nexus_http_setting_name     = "be-htst-nexus"
  gitea_http_setting_name     = "be-htst-gitea"
  api_probe_name              = "hp-api"
  nexus_probe_name            = "hp-nexus"
  gitea_probe_name            = "hp-gitea"

  insecure_listener_name = "httplstn-insecure"
  secure_listener_name   = "httplstn-secure"

  redirect_request_routing_rule_name = "rqrt-redirect"
  request_routing_rule_name          = "rqrt-application"
  redirect_configuration_name        = "rdrcfg-tosecure"

  certificate_name = "cert-primary"
}
