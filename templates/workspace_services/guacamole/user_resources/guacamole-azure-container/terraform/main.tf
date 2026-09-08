terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.57.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.7.2"
    }
  }
  backend "azurerm" {}
}

provider "azurerm" {
  subscription_id     = coalesce(var.workspace_subscription_id, data.azurerm_client_config.current.subscription_id)
  storage_use_azuread = true
  features {
    key_vault {
      purge_soft_deleted_secrets_on_destroy = false
    }
  }
}

provider "azurerm" {
  alias = "core"
  features {}
}

variable "tre_id" { type = string }
variable "workspace_id" { type = string }
variable "parent_service_id" { type = string }
variable "tre_resource_id" { type = string }
variable "owner_id" { type = string }
variable "image_name" { type = string }
variable "image_tag" {
  type    = string
  default = ""
}
variable "container_size" {
  type    = string
  default = "2 CPU | 8GB RAM"

  validation {
    condition     = contains(["2 CPU | 4GB RAM", "2 CPU | 8GB RAM", "4 CPU | 16GB RAM"], var.container_size)
    error_message = "Container size must be one of the supported CPU and memory profiles."
  }
}
variable "workspace_subscription_id" {
  type    = string
  default = ""
}
variable "shared_storage_access" {
  type    = bool
  default = false
}

locals {
  suffix              = "${var.tre_id}-ws-${substr(var.workspace_id, -4, -1)}"
  hostname            = "desktop-${var.tre_resource_id}"
  storage_name        = lower(replace("stg${substr(local.suffix, -8, -1)}", "-", ""))
  image_tag_from_file = replace(replace(replace(file("${path.module}/../image/version.txt"), "__version__ = \"", ""), "\"", ""), "\n", "")
  image_tag           = var.image_tag == "" ? local.image_tag_from_file : var.image_tag
  container_sizes = {
    "2 CPU | 4GB RAM"  = { cpu = 2, memory = 4 }
    "2 CPU | 8GB RAM"  = { cpu = 2, memory = 8 }
    "4 CPU | 16GB RAM" = { cpu = 4, memory = 16 }
  }
  selected_container_size = local.container_sizes[var.container_size]
  tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.parent_service_id
    tre_user_resource_id     = var.tre_resource_id
    tre_user_id              = var.owner_id
    tre_user_username        = "researcher"
  }
}

data "azurerm_client_config" "current" {
  provider = azurerm.core
}
data "azurerm_resource_group" "ws" { name = "rg-${local.suffix}" }
data "azurerm_virtual_network" "ws" {
  name                = "vnet-${local.suffix}"
  resource_group_name = data.azurerm_resource_group.ws.name
}
data "azurerm_subnet" "aci" {
  name                 = "ACI-${var.parent_service_id}"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_resource_group.ws.name
}
data "azurerm_key_vault" "ws" {
  name                = lower("kv-${substr(local.suffix, -20, -1)}")
  resource_group_name = data.azurerm_resource_group.ws.name
}
data "azurerm_storage_account" "ws" {
  count               = var.shared_storage_access ? 1 : 0
  name                = local.storage_name
  resource_group_name = data.azurerm_resource_group.ws.name
}
data "azurerm_linux_web_app" "guacamole" {
  name                = "guacamole-${local.suffix}-svc-${substr(var.parent_service_id, -4, -1)}"
  resource_group_name = data.azurerm_resource_group.ws.name
}
data "azurerm_container_registry" "acr" {
  provider            = azurerm.core
  name                = "acr${replace(var.tre_id, "-", "")}"
  resource_group_name = var.tre_id
}
data "azurerm_public_ip" "gateway" {
  provider            = azurerm.core
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

resource "random_password" "desktop" {
  length  = 32
  special = false
}
resource "azurerm_key_vault_secret" "credentials" {
  name         = "${local.hostname}-admin-credentials"
  value        = "researcher\n${random_password.desktop.result}"
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.tags
}
resource "azurerm_user_assigned_identity" "pull" {
  name                = "id-${local.hostname}"
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location
  tags                = local.tags
}
resource "azurerm_role_assignment" "pull" {
  provider                         = azurerm.core
  scope                            = data.azurerm_container_registry.acr.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_user_assigned_identity.pull.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_container_group" "desktop" {
  name                = local.hostname
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location
  os_type             = "Linux"
  ip_address_type     = "Private"
  subnet_ids          = [data.azurerm_subnet.aci.id]
  restart_policy      = "Always"
  tags                = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.pull.id]
  }
  image_registry_credential {
    server                    = data.azurerm_container_registry.acr.login_server
    user_assigned_identity_id = azurerm_user_assigned_identity.pull.id
  }
  dns_config {
    nameservers = length(data.azurerm_virtual_network.ws.dns_servers) > 0 ? data.azurerm_virtual_network.ws.dns_servers : ["168.63.129.16"]
  }
  container {
    name   = "desktop"
    image  = "${data.azurerm_container_registry.acr.login_server}/${var.image_name}:${local.image_tag}"
    cpu    = local.selected_container_size.cpu
    memory = local.selected_container_size.memory
    ports {
      port     = 3389
      protocol = "TCP"
    }
    environment_variables = {
      NEXUS_PROXY_URL = "https://nexus-${data.azurerm_public_ip.gateway.fqdn}"
    }
    secure_environment_variables = {
      DESKTOP_PASSWORD = random_password.desktop.result
    }
    readiness_probe {
      exec                  = ["bash", "-c", "exec 3<>/dev/tcp/127.0.0.1/3389"]
      initial_delay_seconds = 5
      period_seconds        = 5
      failure_threshold     = 3
    }
    dynamic "volume" {
      for_each = var.shared_storage_access ? [1] : []
      content {
        name                 = "workspace-files"
        mount_path           = "/fileshares/vm-shared-storage"
        read_only            = false
        share_name           = "vm-shared-storage"
        storage_account_name = data.azurerm_storage_account.ws[0].name
        storage_account_key  = data.azurerm_storage_account.ws[0].primary_access_key
      }
    }
  }
  depends_on = [azurerm_role_assignment.pull, azurerm_key_vault_secret.credentials]
}

output "ip" { value = azurerm_container_group.desktop.ip_address }
output "hostname" { value = local.hostname }
output "azure_resource_id" { value = azurerm_container_group.desktop.id }
output "connection_uri" {
  value = "https://${data.azurerm_linux_web_app.guacamole.default_hostname}/?/client/${textencodebase64("${local.hostname}\u0000c\u0000azuretre", "UTF-8")}"
}