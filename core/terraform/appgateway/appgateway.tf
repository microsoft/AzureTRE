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
    name     = coalesce(var.app_gateway_sku, "Standard_v2")
    tier     = coalesce(var.app_gateway_sku, "Standard_v2")
    capacity = 1
  }

  firewall_policy_id = var.app_gateway_sku == "WAF_v2" ? azurerm_web_application_firewall_policy.waf[0].id : null

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
    public_ip_address_id = azurerm_public_ip.appgwpip.id
  }

  # Primary SSL cert linked to KeyVault
  ssl_certificate {
    name                = local.certificate_name
    key_vault_secret_id = azurerm_key_vault_certificate.tlscert.secret_id
  }

  # SSL policy
  ssl_policy {
    policy_type = "Predefined"
    policy_name = "AppGwSslPolicy20220101"
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

    match {
      status_code = [
        "200-399"
      ]
    }
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
      paths                      = ["/api/*", "/openapi.json"]
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

  # ssl_certificate: we don't want Terraform to revert certificate cycle changes. We assume the certificate will be renewed in keyvault.
  # zones: see https://github.com/hashicorp/terraform-provider-azurerm/issues/30129
  lifecycle { ignore_changes = [ssl_certificate, zones, tags] }

}

resource "azurerm_web_application_firewall_policy" "waf" {

  // only create WAF policy when App Gateway sku.tier == "WAF_v2"
  count = var.app_gateway_sku == "WAF_v2" ? 1 : 0

  name                = "wafpolicy-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location

  policy_settings {
    enabled = true
    mode    = "Detection"
  }

  managed_rules {
    managed_rule_set {
      type    = "OWASP"
      version = 3.2
    }
  }

  // once created ignore policy_settings and rulesets allow to be managed outside of here
  lifecycle { ignore_changes = [policy_settings, managed_rules] }

  // terraform doesn't handle the downgrade from WAF_v2 > Standard_v2 SKU, this is required to detatch the policy from the app gateway before deletion of the policy
  provisioner "local-exec" {
    when    = destroy
    command = <<EOT
          APP_GATEWAY_ID=$(az network application-gateway waf-policy show --name ${self.name} --resource-group ${self.resource_group_name} --query applicationGateways[0].id --output tsv)
          az network application-gateway update --ids $APP_GATEWAY_ID --set firewallPolicy=null --set sku.name=Standard_v2 --set sku.tier=Standard_v2
        EOT
  }
}

resource "azurerm_monitor_diagnostic_setting" "agw" {
  name                       = "diagnostics-agw-${var.tre_id}"
  target_resource_id         = azurerm_application_gateway.agw.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = setintersection(data.azurerm_monitor_diagnostic_categories.agw.log_category_types, local.appgateway_diagnostic_categories_enabled)
    content {
      category = enabled_log.value
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }

  lifecycle { ignore_changes = [log_analytics_destination_type] }
}


