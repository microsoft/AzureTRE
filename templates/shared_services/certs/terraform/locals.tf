locals {
  staticweb_storage_name = lower(replace("stwebcerts${var.tre_id}", "-", ""))

  staticweb_backend_pool_name = "beap-certs-staticweb"
  app_path_map_name           = "upm-certs"
  redirect_path_map_name      = "upm-certs-redirect"

  insecure_frontend_port_name = "feport-certs-insecure"
  secure_frontend_port_name   = "feport-certs-secure"

  frontend_ip_configuration_name = "feip-certs-public"

  staticweb_http_setting_name = "be-htst-certs-staticweb"

  insecure_listener_name = "httplstn-certs-insecure"
  secure_listener_name   = "httplstn-certs-secure"

  redirect_request_routing_rule_name = "rqrt-certs-redirect"
  request_routing_rule_name          = "rqrt-certs-application"
  redirect_configuration_name        = "rdrcfg-certs-tosecure"

  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }

  cmk_name                 = "tre-encryption-${var.tre_id}"
  encryption_identity_name = "id-encryption-${var.tre_id}"
  password_name            = "${var.cert_name}-password"
}
