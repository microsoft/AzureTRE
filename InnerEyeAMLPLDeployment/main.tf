provider "azurerm" {
    features {}
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "rg"{
    name =  "${var.resource_name_prefix}rg"
    location = var.location
    tags = {
        environment = var.tag
        Source        = "https://github.com/microsoft/AzureTRE/"
  }
}

resource "azurerm_virtual_network" "vnet" {
  name = "${var.resource_name_prefix}vnet"
  address_space = [var.address_space]
  resource_group_name = azurerm_resource_group.rg.name
  location = azurerm_resource_group.rg.location
}

resource "azurerm_subnet" "default" {
  name = "default"
  address_prefixes = [var.default_address_space]
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies = true
  virtual_network_name = azurerm_virtual_network.vnet.name
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "inference" {
  name = "inference"
  address_prefixes = [var.inference_address_space]
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies = true
  virtual_network_name = azurerm_virtual_network.vnet.name
  resource_group_name = azurerm_resource_group.rg.name

   delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet" "AzureFirewallSubnet" {
  name = "AzureFirewallSubnet" # mandatory name -do not rename-
  address_prefixes = [var.fw_address_space]
  virtual_network_name = azurerm_virtual_network.vnet.name
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_public_ip" "fwpip" {
  name = "${var.resource_name_prefix}fwpip"
  resource_group_name = azurerm_resource_group.rg.name
  location = azurerm_resource_group.rg.location
  allocation_method = "Static"
  sku = "Standard"
}

resource "azurerm_firewall" "fw" {
  depends_on=[azurerm_public_ip.fwpip]
  name = "${var.resource_name_prefix}fw"
  resource_group_name = azurerm_resource_group.rg.name
  location = azurerm_resource_group.rg.location
  ip_configuration {
    name = "${var.resource_name_prefix}fw-config"
    subnet_id = azurerm_subnet.AzureFirewallSubnet.id
    public_ip_address_id = azurerm_public_ip.fwpip.id
  }
}

resource "azurerm_route_table" "rt" {
  name                          = "${var.resource_name_prefix}RouteTable"
  location                      = azurerm_resource_group.rg.location
  resource_group_name           = azurerm_resource_group.rg.name
  disable_bgp_route_propagation = false

  route {
    name           = "DefaultRoute"
    address_prefix = "0.0.0.0/0"
    next_hop_type  = "VirtualAppliance"
    next_hop_in_ip_address = azurerm_firewall.fw.ip_configuration.0.private_ip_address
  }
}

resource "azurerm_subnet_route_table_association" "rtsubnet" {
  subnet_id      = azurerm_subnet.default.id
  route_table_id = azurerm_route_table.rt.id
}

resource "azurerm_key_vault" "kv" {
  name                = "${var.resource_name_prefix}kv"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = "standard"
  purge_protection_enabled = true
  tenant_id           = data.azurerm_client_config.current.tenant_id
}

resource "azurerm_private_dns_zone" "vaultcore" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "vaultcorelink" {
  name                  = "vaultcorelink"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.vaultcore.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

resource "azurerm_private_endpoint" "kvpe" {
  name                = "${var.resource_name_prefix}kvpe"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.default.id

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.vaultcore.id]
  }

  private_service_connection {
    name                           = "${var.resource_name_prefix}kvpesc"
    private_connection_resource_id = azurerm_key_vault.kv.id
    is_manual_connection           = false
    subresource_names              = ["Vault"]
  }
}

resource "azurerm_storage_account" "stg" {
  name                     = "${var.resource_name_prefix}stg"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

}

resource "azurerm_private_dns_zone" "filecore" {
  name                = "privatelink.file.core.windows.net"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone" "blobcore" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "filecorelink" {
  name                  = "filecorelink"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.filecore.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

resource "azurerm_private_dns_zone_virtual_network_link" "blobcorelink" {
  name                  = "blobcorelink"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.blobcore.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

resource "azurerm_private_endpoint" "stgfilepe" {
  name                = "${var.resource_name_prefix}stgfilepe"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.default.id

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.filecore.id]
  }

  private_service_connection {
    name                           = "${var.resource_name_prefix}stgfilepesc"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["File"]
  }
}

resource "azurerm_private_endpoint" "stgblobpe" {
  name                = "${var.resource_name_prefix}stgblobpe"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.default.id

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "${var.resource_name_prefix}stgblobpesc"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

resource "azurerm_container_registry" "acr" {
  name                     = "${var.resource_name_prefix}acr"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  sku                      = "Premium"
  admin_enabled            = false
}

resource "azurerm_private_dns_zone" "azurecr" {
  name                = "privatelink.azurecr.io"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "azurecrlink" {
  name                  = "azurecrlink"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.azurecr.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

resource "azurerm_private_endpoint" "acrpe" {
  name                = "${var.resource_name_prefix}acrpe"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.default.id

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.azurecr.id]
  }

  private_service_connection {
    name                           = "${var.resource_name_prefix}acrpesc"
    private_connection_resource_id = azurerm_container_registry.acr.id
    is_manual_connection           = false
    subresource_names              = ["registry"]
  }
}

resource "azurerm_application_insights" "ai" {
  name                = "${var.resource_name_prefix}ai"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
}

resource "azurerm_machine_learning_workspace" "ml" {
  name                    = "${var.resource_name_prefix}ml"
  location                = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name
  application_insights_id = azurerm_application_insights.ai.id
  key_vault_id            = azurerm_key_vault.kv.id
  storage_account_id      = azurerm_storage_account.stg.id

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_private_dns_zone" "azureml" {
  name                = "privatelink.api.azureml.ms"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone" "notebooks" {
  name                = "privatelink.notebooks.azure.net"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "azuremllink" {
  name                  = "azuremllink"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.azureml.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

resource "azurerm_private_dns_zone_virtual_network_link" "notebookslink" {
  name                  = "notebookslink"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.notebooks.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

resource "azurerm_private_endpoint" "mlpe" {
  name                = "${var.resource_name_prefix}mlpe"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.default.id

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.azureml.id, azurerm_private_dns_zone.notebooks.id]
  }

  private_service_connection {
    name                           = "${var.resource_name_prefix}mlpesc"
    private_connection_resource_id = azurerm_machine_learning_workspace.ml.id
    is_manual_connection           = false
    subresource_names              = ["amlworkspace"]
  }
}

resource "azurerm_network_interface" "vmnic" {
  name                = "${var.resource_name_prefix}nic"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "${var.resource_name_prefix}vmnetconfig"
    subnet_id                     = azurerm_subnet.default.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_virtual_machine" "vm" {
  name                  = "${var.resource_name_prefix}vm"
  location              = azurerm_resource_group.rg.location
  resource_group_name   = azurerm_resource_group.rg.name
  network_interface_ids = [azurerm_network_interface.vmnic.id]
  vm_size               = "Standard_DS3_v2"

  delete_os_disk_on_termination = true
  delete_data_disks_on_termination = true

  storage_image_reference {
    publisher = "microsoft-dsvm"
    offer     = "dsvm-win-2019"
    sku       = "server-2019"
    version   = "latest"
  }

  os_profile_windows_config {
    provision_vm_agent = true
    enable_automatic_upgrades = true
  }

  storage_os_disk {
    name              = "myosdisk1"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }
  os_profile {
    computer_name  = "jumpbox"
    admin_username = var.username
    admin_password = var.password
  }
}

resource "azurerm_firewall_nat_rule_collection" "natrulecollection" {
  name                = "${var.resource_name_prefix}natrulecollection"
  azure_firewall_name = azurerm_firewall.fw.name
  resource_group_name = azurerm_resource_group.rg.name
  priority            = 200
  action              = "Dnat"

  rule {
    name = "jumpboxrdp"

    source_addresses = [
      "*"
    ]

    destination_ports = [
      "3389"
    ]

    destination_addresses = [
      azurerm_public_ip.fwpip.ip_address
    ]

    translated_port = 3389

    translated_address = azurerm_network_interface.vmnic.private_ip_address

    protocols = [
      "TCP"
    ]
  }
}

resource "azurerm_firewall_application_rule_collection" "apprulecollection" {
  name                = "${var.resource_name_prefix}apprulecollection"
  azure_firewall_name = azurerm_firewall.fw.name
  resource_group_name = azurerm_resource_group.rg.name
  priority            = 200
  action              = "Allow"

  rule {
    name = "allowMLrelated"

    source_addresses = [
      var.default_address_space
    ]

    target_fqdns =  var.allowedURLs
    

    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }
  }
}

resource "azurerm_firewall_application_rule_collection" "innereyeapprulecollection" {
  name                = "${var.resource_name_prefix}innereyeapprulecollection"
  azure_firewall_name = azurerm_firewall.fw.name
  resource_group_name = azurerm_resource_group.rg.name
  priority            = 210
  action              = "Allow"

  rule {
    name = "allowInnerEyerelated"

    source_addresses = [
      var.default_address_space
    ]

    target_fqdns =  var.allowedInnerEyeURLs
    

    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }
  }
}

resource "azurerm_firewall_network_rule_collection" "networkrulecollection" {
  name                = "${var.resource_name_prefix}networkrulecollection"
  azure_firewall_name = azurerm_firewall.fw.name
  resource_group_name = azurerm_resource_group.rg.name
  priority            = 200
  action              = "Allow"

  rule {
    name = "allowStorage"

    source_addresses = [
      var.default_address_space
    ]

    destination_ports = [
      "*"
    ]

    destination_addresses = var.allowedServiceTags

    protocols = [
      "TCP"
    ]
  }
}

resource "azurerm_app_service_plan" "inference-app-service-plan" {
  name                = "${var.resource_name_prefix}inf-asp"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "Linux"
  reserved            = "true"

  sku {
    tier = "PremiumV2"
    size = "P1v2"
  }
}

resource "azurerm_app_service" "inference-app-service" {
  name                = "${var.resource_name_prefix}inf-app"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  app_service_plan_id = azurerm_app_service_plan.inference-app-service-plan.id
  https_only          = true
  
  site_config {
    always_on = true
    http2_enabled = true
  }
  
  app_settings = {
    "WEBSITE_VNET_ROUTE_ALL" = "1",
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "True"
  }

}

resource "azurerm_app_service_virtual_network_swift_connection" "inference-vnet" {
  app_service_id = azurerm_app_service.inference-app-service.id
  subnet_id      = azurerm_subnet.inference.id
}

resource "azuread_application" "inference-adapp" {
  display_name   = "${var.resource_name_prefix}inferenceadapp"
}

resource "azuread_service_principal" "inference-adappspn" {
  application_id = azuread_application.inference-adapp.application_id
}

# Random unique password
resource "random_string" "password" {
  length  = 17
  special = true
  upper   = true
  override_special = "-_=+[]#%"
}

resource "azuread_application_password" "appspnpwd" {
  application_object_id = azuread_application.inference-adapp.object_id
  description           = "password"
  value                 = random_string.password.result
  start_date            = timestamp()
  end_date              = timeadd(timestamp(), "17496h")
}

resource "azurerm_role_assignment" "spnContributor" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.inference-adappspn.id
}
