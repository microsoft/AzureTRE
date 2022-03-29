variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "nexus_allowed_fqdns" {
  type        = string
  description = "comma seperated string of allowed FQDNs for Nexus"
  default     = "*pypi.org,files.pythonhosted.org,security.ubuntu.com,archive.ubuntu.com,keyserver.ubuntu.com,repo.anaconda.com,*.docker.com,*.docker.io,conda.anaconda.org,azure.archive.ubuntu.com, packages.microsoft.com"
}
