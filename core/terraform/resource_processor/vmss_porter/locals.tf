locals {
  version = replace(replace(replace(data.local_file.version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }

  azure_environment = lookup({
    "public"       = "AzureCloud"
    "usgovernment" = "AzureUSGovernment"
  }, var.arm_environment, "AzureCloud")

  rp_bundle_values_all       = merge(var.rp_bundle_values, { tre_url = var.tre_url })
  rp_bundle_values_dic       = [for key in keys(local.rp_bundle_values_all) : "RP_BUNDLE_${key}=${local.rp_bundle_values_all[key]}"]
  rp_bundle_values_formatted = join("\n      ", local.rp_bundle_values_dic)
}
