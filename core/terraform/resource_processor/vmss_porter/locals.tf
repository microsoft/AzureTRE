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
}
