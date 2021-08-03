variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}


variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}


variable "gitea_username" {
  type        = string
  description = "Admin username of gitea"
}


variable "gitea_passwd" {
  type        = string
  description = "Admin password of gitea"
}


variable "gitea_email" {
  type        = string
  description = "Admin email of gitea"
}
