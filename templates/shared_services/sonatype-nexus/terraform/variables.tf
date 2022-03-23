variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "nexus_storage_limit" {
  type        = number
  description = "Space allocated in GB for the Nexus data in Azure Files Share"
  default     = 1024
}

variable "nexus_allowed_fqdns" {
  type        = string
  description = "comma seperated string of allowed FQDNs for Nexus"
  default     = "*pypi.org,files.pythonhosted.org,security.ubuntu.com,archive.ubuntu.com,repo.anaconda.com,*.docker.com,*.docker.io,conda.anaconda.org"
}

variable "nexus_properties_path" {
  type        = string
  description = "relative path of nexus properties file"
  default     = "/cnab/app/nexus.properties"
}
