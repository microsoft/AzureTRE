resource "azurerm_public_ip" "appgwpip" {
  name                = "pip-cert-${var.domain_prefix}-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  allocation_method   = "Static"
  sku                 = "Standard"
  domain_name_label   = "${var.domain_prefix}-${var.tre_id}"
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags, zones] }
}

resource "azurerm_user_assigned_identity" "agw_id" {
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  name                = "id-agw-certs-${var.tre_id}"
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_application_gateway" "agw" {
  name                = "agw-certs-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  tags                = local.tre_shared_service_tags

  sku {
    name     = "Basic"
    tier     = "Basic"
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
    subnet_id = data.azurerm_subnet.app_gw_subnet.id
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
    name                = "cert-primary"
    key_vault_secret_id = azurerm_key_vault_certificate.tlscert.secret_id
  }

  # Backend pool with the static website in storage account.
  backend_address_pool {
    name  = local.staticweb_backend_pool_name
    fqdns = [azurerm_storage_account.staticweb.primary_web_host]
  }

  # Backend settings for static web.
  backend_http_settings {
    name                                = local.staticweb_http_setting_name
    cookie_based_affinity               = "Disabled"
    port                                = 443
    protocol                            = "Https"
    request_timeout                     = 60
    pick_host_name_from_backend_address = true
  }

  # Public HTTPS listener
  http_listener {
    name                           = local.secure_listener_name
    frontend_ip_configuration_name = local.frontend_ip_configuration_name
    frontend_port_name             = local.secure_frontend_port_name
    protocol                       = "Https"
    ssl_certificate_name           = "cert-primary"
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

  # Default traffic is routed to the static website.
  url_path_map {
    name                               = local.app_path_map_name
    default_backend_address_pool_name  = local.staticweb_backend_pool_name
    default_backend_http_settings_name = local.staticweb_http_setting_name

    path_rule {
      name                       = "all"
      paths                      = ["/*"]
      backend_address_pool_name  = local.staticweb_backend_pool_name
      backend_http_settings_name = local.staticweb_http_setting_name
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
  lifecycle {
    ignore_changes = [
      ssl_certificate,
      tags
    ]
  }

  depends_on = [
    azurerm_role_assignment.keyvault_appgwcerts_role,
  ]
}
