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

  rp_bundle_values_all = merge(var.rp_bundle_values, {
    // Add any additional settings like ones from the config.yaml here
    // to make them available for bundles.
    enable_cmk_encryption                  = var.enable_cmk_encryption
    key_store_id                           = var.key_store_id
    ui_client_id                           = var.ui_client_id
    auto_grant_workspace_consent           = var.auto_grant_workspace_consent
    enable_airlock_malware_scanning        = var.enable_airlock_malware_scanning
    airlock_malware_scan_result_topic_name = var.airlock_malware_scan_result_topic_name
    core_api_client_id                     = var.core_api_client_id
    firewall_policy_id                     = var.firewall_policy_id
  })
  rp_bundle_values_dic       = [for key in keys(local.rp_bundle_values_all) : "RP_BUNDLE_${key}=${local.rp_bundle_values_all[key]}"]
  rp_bundle_values_formatted = join("\n      ", local.rp_bundle_values_dic)

}
