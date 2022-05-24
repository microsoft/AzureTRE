locals {
  app_insights_name = "appi-${var.tre_id}"
}

locals {
  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }
}
