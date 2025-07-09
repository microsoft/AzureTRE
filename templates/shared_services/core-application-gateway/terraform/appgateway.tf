resource "azurerm_user_assigned_identity" "agw_id" {
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.core.location
  name                = "id-agw-${var.tre_id}"
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_application_gateway" "agw" {
  name                = "agw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
  location            = data.azurerm_resource_group.core.location
  tags                = local.tre_core_tags

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 1
  }

  # User-assign managed identify id required to access certificate in KeyVault
  identity {
    type         = "UserAssigned"
    identity_ids = [data.azurerm_user_assigned_identity.agw.id]
  }

  # Internal subnet for gateway backend.
  gateway_ip_configuration {
    name      = "gateway-ip-configuration"
    subnet_id = data.azurerm_subnet.agw.id
  }

  frontend_port {
    name = local.insecure_frontend_port_name
    port = 80
  }

  frontend_port {
    name = local.secure_frontend_port_name
    port = 443
  }

  # Public front-end
  frontend_ip_configuration {
    name                 = local.frontend_ip_configuration_name
    public_ip_address_id = data.azurerm_public_ip.agw.id
  }

  # Primary SSL cert linked to KeyVault
  ssl_certificate {
    name                = var.certificate_name
    key_vault_secret_id = data.azurerm_key_vault_certificate.tlscert.secret_id
  }

  # Backend pool with the static website in storage account.
  backend_address_pool {
    name  = local.staticweb_backend_pool_name
    fqdns = ["${var.ui_app_service}.azurewebsites.net"]
  }

  # Backend pool with the API App Service.
  backend_address_pool {
    name  = local.api_backend_pool_name
    fqdns = [data.azurerm_linux_web_app.api.default_hostname]
  }

  dynamic "backend_address_pool" {
    for_each = { for i, v in local.dynamic_backends : i => v }
    content {
      name  = "beap-${backend_address_pool.value.name}"
      fqdns = [regex(local.url_parts_pattern, "//${trimprefix(trimprefix(backend_address_pool.value.fqdn, "http://"), "https://")}").fqdn]
    }
  }

  # Backend settings for api.
  # Using custom probe to test specific health endpoint
  backend_http_settings {
    name                                = local.api_http_setting_name
    cookie_based_affinity               = "Disabled"
    port                                = 443
    protocol                            = "Https"
    request_timeout                     = 60
    pick_host_name_from_backend_address = true
    probe_name                          = local.api_probe_name
  }

  backend_http_settings {
    name                                = local.dynamic_backend_settings_name
    cookie_based_affinity               = "Disabled"
    port                                = 443
    protocol                            = "Https"
    pick_host_name_from_backend_address = true
  }

  # Backend settings for static web.
  # Using default probe to test root path (/)
  backend_http_settings {
    name                                = local.staticweb_http_setting_name
    cookie_based_affinity               = "Disabled"
    port                                = 443
    protocol                            = "Https"
    request_timeout                     = 60
    pick_host_name_from_backend_address = true
  }

  # Custom health probe for API.
  probe {
    name                                      = local.api_probe_name
    pick_host_name_from_backend_http_settings = true
    interval                                  = 15
    protocol                                  = "Https"
    # Use the /api/ping endpoint to verify that we can connect to the API
    # This still allows the richer information from /api/health to be queried
    # in the event of a component being unavailable
    # It also avoids incurring the Azure Management API calls to resource processor
    # when not needed (which can cause throttling)
    path                = "/api/ping"
    timeout             = "30"
    unhealthy_threshold = "3"
  }

  # Public HTTPS listener
  http_listener {
    name                           = local.secure_listener_name
    frontend_ip_configuration_name = local.frontend_ip_configuration_name
    frontend_port_name             = local.secure_frontend_port_name
    protocol                       = "Https"
    ssl_certificate_name           = var.certificate_name
  }

  # Public HTTP listener
  http_listener {
    name                           = local.insecure_listener_name
    frontend_ip_configuration_name = local.frontend_ip_configuration_name
    frontend_port_name             = local.insecure_frontend_port_name
    protocol                       = "Http"
  }

  request_routing_rule {
    name               = local.request_routing_rule_name
    rule_type          = "PathBasedRouting"
    http_listener_name = local.secure_listener_name
    url_path_map_name  = local.app_path_map_name
    priority           = 100
  }

  # Routing rule to redirect non-secure traffic to HTTPS
  request_routing_rule {
    name               = local.redirect_request_routing_rule_name
    rule_type          = "PathBasedRouting"
    http_listener_name = local.insecure_listener_name
    url_path_map_name  = local.redirect_path_map_name
    priority           = 10
  }

  # Default traffic is routed to the static website. Exception is API.
  url_path_map {
    name                               = local.app_path_map_name
    default_backend_address_pool_name  = local.staticweb_backend_pool_name
    default_backend_http_settings_name = local.staticweb_http_setting_name

    path_rule {
      name                       = "api"
      paths                      = ["/api/*", "/openapi.json"]
      backend_address_pool_name  = local.api_backend_pool_name
      backend_http_settings_name = local.api_http_setting_name
    }

    dynamic "path_rule" {
      for_each = { for i, v in local.dynamic_backends : i => v if v.fqdn != "" }
      content {
        name                       = path_rule.value.name
        paths                      = ["/${path_rule.value.name}*"]
        backend_address_pool_name  = "beap-${path_rule.value.name}"
        backend_http_settings_name = local.dynamic_backend_settings_name
        rewrite_rule_set_name      = local.dynamic_rewrite_set
      }
    }
  }

  # Redirect any HTTP traffic to HTTPS unless its the ACME challenge path used for LetsEncrypt validation.
  url_path_map {
    name                                = local.redirect_path_map_name
    default_redirect_configuration_name = local.redirect_configuration_name

    path_rule {
      name                       = "acme"
      paths                      = ["/.well-known/acme-challenge/*"]
      backend_address_pool_name  = local.staticweb_backend_pool_name
      backend_http_settings_name = local.staticweb_http_setting_name
    }
  }

  # Redirect to HTTPS
  redirect_configuration {
    name                 = local.redirect_configuration_name
    redirect_type        = "Permanent"
    target_listener_name = local.secure_listener_name
    include_path         = true
    include_query_string = true
  }

  dynamic "rewrite_rule_set" {
    for_each = length(local.dynamic_backends) == 0 ? [0] : [1]
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
        name          = "URL-remove-first-part"
        rule_sequence = 200
        condition {
          pattern     = "^\\/(.+?)\\/(.*)"
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
  lifecycle { ignore_changes = [ssl_certificate, tags] }

}
