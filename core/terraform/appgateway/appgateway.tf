resource "azurerm_public_ip" "appgwpip" {
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  allocation_method   = "Static" # Static IPs are allocated immediately
  sku                 = "Standard"
  domain_name_label   = var.tre_id
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags, zones] }
}

resource "azurerm_user_assigned_identity" "agw_id" {
  resource_group_name = var.resource_group_name
  location            = var.location
  name                = "id-agw-${var.tre_id}"
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_application_gateway" "agw" {
  name                = "agw-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = local.tre_core_tags

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 1
  }

  # User-assign managed identify id required to access certificate in KeyVault
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.agw_id.id]
  }

  # Internal subnet for gateway backend.
  gateway_ip_configuration {
    name      = "gateway-ip-configuration"
    subnet_id = var.app_gw_subnet
  }

  # HTTP Port
  frontend_port {
    name = local.insecure_frontend_port_name
    port = 80
  }

  # HTTPS Port
  frontend_port {
    name = local.secure_frontend_port_name
    port = 443
  }

  # Public front-end
  frontend_ip_configuration {
    name                 = local.frontend_ip_configuration_name
    public_ip_address_id = azurerm_public_ip.appgwpip.id
  }

  # Primary SSL cert linked to KeyVault
  ssl_certificate {
    name                = local.certificate_name
    key_vault_secret_id = azurerm_key_vault_certificate.tlscert.secret_id
  }

  # Backend pool with the static website in storage account.
  backend_address_pool {
    name  = local.staticweb_backend_pool_name
    fqdns = [azurerm_storage_account.staticweb.primary_web_host]
  }

  # Backend pool with the API App Service.
  backend_address_pool {
    name  = local.api_backend_pool_name
    fqdns = [var.api_fqdn]
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
    ssl_certificate_name           = local.certificate_name
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
      paths                      = ["/api/*", "/api/docs", "/openapi.json", "/api/docs/oauth2-redirect"]
      backend_address_pool_name  = local.api_backend_pool_name
      backend_http_settings_name = local.api_http_setting_name
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

  # We don't want Terraform to revert certificate cycle changes. We assume the certificate will be renewed in keyvault.
  lifecycle { ignore_changes = [ssl_certificate, tags] }

}

resource "azurerm_monitor_diagnostic_setting" "agw" {
  name                       = "diagnostics-agw-${var.tre_id}"
  target_resource_id         = azurerm_application_gateway.agw.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  # log_analytics_destination_type = "Dedicated"

  dynamic "enabled_log" {
    for_each = ["ApplicationGatewayAccessLog", "ApplicationGatewayPerformanceLog", "ApplicationGatewayFirewallLog"]
    content {
      category = enabled_log.value

      retention_policy {
        enabled = true
        days    = 365
      }
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true

    retention_policy {
      enabled = true
      days    = 365
    }
  }
}


