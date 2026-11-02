variable "tre_id" {
  type = string
}
variable "tre_resource_id" {
  type = string
}
variable "arm_environment" {
  type = string
}
variable "enable_cmk_encryption" {
  type    = bool
  default = false
}
variable "key_store_id" {
  type = string
}
variable "cluster_address_spaces" {
  type        = string
  description = "Address spaces of cluster nodes that connect to the CycleCloud server on port 9443 (base 64 JSON array)"

  validation {
    condition = try(alltrue([
      for cidr in jsondecode(base64decode(var.cluster_address_spaces)) :
      can(cidrnetmask(cidr))
    ]), false)
    error_message = "cluster_address_spaces must be a list of IPv4 address ranges in CIDR format, for example 10.1.4.0/24."
  }
}
