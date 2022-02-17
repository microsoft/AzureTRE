variable "tre_id" {}
variable "location" {}
variable "resource_group_name" {}
variable "log_analytics_workspace_id" {}
variable "shared_subnet" {
  type = object({
    id               = string
    address_prefixes = list(string)
  })
  description = "The ID of the shared subnet"
}

variable "firewall_subnet" {
  type = object({
    id               = string
    address_prefixes = list(string)
  })
  description = "The ID of the firewall subnet"
}

variable "resource_processor_subnet" {
  type = object({
    id               = string
    address_prefixes = list(string)
  })
  description = "The ID of the resource_processor subnet"
}

variable "web_app_subnet" {
  type = object({
    id               = string
    address_prefixes = list(string)
  })
  description = "The ID of the web app subnet"
}

variable "stateful_resources_locked" {
  type    = bool
  default = true
}
