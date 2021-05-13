locals {
  backend_address_pool_name      = "beap-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  management_api_backend_address_pool_name = "beap-${var.resource_name_prefix}-${var.environment}-${var.tre_id}-management-api"
  management_api_url_path_map_name_pool_name = "upm-${var.resource_name_prefix}-${var.environment}-${var.tre_id}-management-api"
  frontend_port_name             = "feport-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  frontend_ip_configuration_name = "feip-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  http_setting_name              = "be-htst-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  listener_name                  = "httplstn-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  request_routing_rule_name      = "rqrt-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  redirect_configuration_name    = "rdrcfg-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
}