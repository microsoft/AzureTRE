resource "azurerm_application_gateway" "agw" {
  count = var.internal_agw_count
  # for_each = toset(local.internal_agw_ips)
  name                = "agw-internal${count.index}-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.core.location
  tags                = local.tre_core_tags

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [data.azurerm_user_assigned_identity.agw.id]
  }

  # Internal subnet for gateway backend.
  gateway_ip_configuration {
    name      = "gateway-ip-configuration"
    subnet_id = data.azurerm_subnet.agw_int.id
  }

  frontend_port {
    name = local.secure_frontend_port_name
    port = 443
  }

  # Public front-end
  frontend_ip_configuration {
    name                          = local.frontend_ip_configuration_name
    private_ip_address            = local.internal_agw_ips[count.index]
    private_ip_address_allocation = "Static"
    subnet_id                     = data.azurerm_subnet.agw_int.id
  }

  ssl_certificate {
    name                = local.certificate_name
    key_vault_secret_id = [for item in data.azurerm_key_vault_secrets.secrets.secrets : item.id if item.name == "${local.keyvault_cert_prefix}-${replace(local.internal_agw_ips[count.index], ".", "-")}"][0]
  }

  # SSL policy
  ssl_policy {
    policy_type = "Predefined"
    policy_name = "AppGwSslPolicy20220101"
  }

  backend_address_pool {
    name  = "beap-default"
    fqdns = [local.default_route_fqdn]
  }

  dynamic "backend_address_pool" {
    for_each = { for i, v in local.dynamic_backends_chunked[count.index] : i => v }
    content {
      name  = "beap-${backend_address_pool.value.name}"
      fqdns = [regex(local.url_parts_pattern, "//${trimprefix(trimprefix(backend_address_pool.value.fqdn, "http://"), "https://")}").fqdn]
    }
  }

  backend_http_settings {
    name                                = local.dynamic_backend_settings_name
    cookie_based_affinity               = "Disabled"
    port                                = 443
    protocol                            = "Https"
    pick_host_name_from_backend_address = true
  }

  # Public HTTP listener
  http_listener {
    name                           = local.secure_listener_name
    frontend_ip_configuration_name = local.frontend_ip_configuration_name
    frontend_port_name             = local.secure_frontend_port_name
    protocol                       = "Https"
    ssl_certificate_name           = local.certificate_name
  }

  request_routing_rule {
    name               = local.request_routing_rule_name
    rule_type          = "PathBasedRouting"
    http_listener_name = local.secure_listener_name
    url_path_map_name  = local.path_map_name
    priority           = 100

  }

  # Default traffic is routed to the static website. Exception is API.
  url_path_map {
    name                               = local.path_map_name
    default_backend_address_pool_name  = "beap-default"
    default_backend_http_settings_name = local.dynamic_backend_settings_name

    dynamic "path_rule" {
      for_each = { for i, v in local.dynamic_backends_chunked[count.index] : i => v if v.fqdn != "" }
      content {
        name                       = path_rule.value.name
        paths                      = ["/${local.internal_agw_backend_url_prefix}${count.index}/${path_rule.value.name}*"]
        backend_address_pool_name  = "beap-${path_rule.value.name}"
        backend_http_settings_name = local.dynamic_backend_settings_name
        rewrite_rule_set_name      = local.dynamic_rewrite_set
      }
    }
  }

  dynamic "rewrite_rule_set" {
    for_each = length(local.dynamic_backends_chunked[count.index]) == 0 ? [0] : [1]
    content {
      name = local.dynamic_rewrite_set
      rewrite_rule {
        name          = "X-Forwarded-Uri"
        rule_sequence = 100
        request_header_configuration {
          header_name  = "X-Forwarded-Uri"
          header_value = "{var_request_uri}"
        }
      }
      rewrite_rule {
        name          = "URL-remove-non-app-prefix"
        rule_sequence = 200
        condition {
          pattern     = "^\\/${local.internal_agw_backend_url_prefix}${count.index}\\/(.+?)\\/(.*)"
          variable    = "var_uri_path"
          ignore_case = true
        }
        url {
          components = "path_only"
          path       = "{var_uri_path_2}"
          reroute    = false
        }
      }
    }
  }

  # We don't want Terraform to revert certificate cycle changes. We assume the certificate will be renewed in keyvault.
  lifecycle { ignore_changes = [tags] }

}



# data "azurerm_log_analytics_workspace" "tre" {
#   name                = "log-${var.tre_id}"
#   resource_group_name = local.core_resource_group_name
# }

# data "azurerm_monitor_diagnostic_categories" "agw" {
#   count = var.internal_agw_count
#   resource_id = azurerm_application_gateway.agw[count.index].id
#   depends_on = [
#     azurerm_application_gateway.agw
#   ]
# }

# resource "azurerm_monitor_diagnostic_setting" "agw" {
#   count = var.internal_agw_count
#   name                       = "diagnostics-${azurerm_application_gateway.agw[count.index].name}"
#   target_resource_id         = azurerm_application_gateway.agw[count.index].id
#   log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

#   dynamic "enabled_log" {
#     for_each = setintersection(data.azurerm_monitor_diagnostic_categories.agw[count.index].log_category_types, local.appgateway_diagnostic_categories_enabled)
#     content {
#       category = enabled_log.value
#     }
#   }

#   metric {
#     category = "AllMetrics"
#     enabled  = true
#   }

#   lifecycle { ignore_changes = [log_analytics_destination_type] }
# }
