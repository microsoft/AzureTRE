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

  cloudconfig_content = templatefile("${path.module}/cloud-config.yaml", {
    docker_registry_server                           = var.docker_registry_server
    terraform_state_container_name                   = var.terraform_state_container_name
    mgmt_resource_group_name                         = var.mgmt_resource_group_name
    mgmt_storage_account_name                        = var.mgmt_storage_account_name
    service_bus_deployment_status_update_queue       = var.service_bus_deployment_status_update_queue
    service_bus_resource_request_queue               = var.service_bus_resource_request_queue
    service_bus_namespace                            = var.service_bus_namespace_fqdn
    vmss_msi_id                                      = azurerm_user_assigned_identity.vmss_msi.client_id
    arm_subscription_id                              = data.azurerm_subscription.current.subscription_id
    arm_tenant_id                                    = data.azurerm_client_config.current.tenant_id
    resource_processor_vmss_porter_image_repository  = var.resource_processor_vmss_porter_image_repository
    resource_processor_vmss_porter_image_tag         = local.version
    app_insights_connection_string                   = var.app_insights_connection_string
    resource_processor_number_processes_per_instance = var.resource_processor_number_processes_per_instance
    key_vault_name                                   = var.key_vault_name
    key_vault_url                                    = var.key_vault_url
    arm_environment                                  = var.arm_environment
    azure_environment                                = local.azure_environment
    aad_authority_url                                = module.terraform_azurerm_environment_configuration.active_directory_endpoint
    microsoft_graph_fqdn                             = regex("(?:(?P<scheme>[^:/?#]+):)?(?://(?P<fqdn>[^/?#:]*))?", module.terraform_azurerm_environment_configuration.microsoft_graph_endpoint).fqdn
    logging_level                                    = var.logging_level
    rp_bundle_values                                 = local.rp_bundle_values_formatted
  })
}
