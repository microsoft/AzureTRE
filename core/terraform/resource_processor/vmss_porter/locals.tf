locals {
  version = replace(replace(replace(data.local_file.version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }

  rp_bundle_values_formatted = join("\n", [for key in keys(var.rp_bundle_values) : "RP_BUNDLE_${key}=${var.rp_bundle_values[key]}"])

  az_cloud_environment = lookup({
    "public"       = "AzureCloud"
    "usgovernment" = "AzureUSGovernment"
    "german"       = "AzureGermanCloud"
    "china"        = "AzureChinaCloud"
  }, var.arm_environment, "AzureCloud")
}
