locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  core_resource_group_name       = "rg-${var.tre_id}"

  # Base name for AI Foundry resources (must be 3-7 characters per AVM module requirement)
  # Using only 3 chars to leave room for module's naming suffixes (storage account names max 24 chars)
  ai_foundry_base_name = lower(substr("ai${local.short_service_id}", 0, 3))

  # Explicit names for BYOR resources to avoid length issues
  storage_account_name = lower(substr("staif${local.short_workspace_id}${local.short_service_id}", 0, 24))
  key_vault_name       = "kv-aif-${local.short_service_id}"

  workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }

  # Parse OpenAI model from "model_name | version" format
  openai_model = {
    name    = trimspace(split("|", var.openai_model)[0])
    version = trimspace(split("|", var.openai_model)[1])
  }
}
