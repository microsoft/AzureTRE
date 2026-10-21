locals {
  # The key store for encryption keys could either be external or created by terraform
  key_store_id = var.enable_cmk_encryption ? (try(length(var.external_key_store_id), 0) > 0 ? var.external_key_store_id : azurerm_key_vault.encryption_kv[0].id) : null

  # CI ownership tags. Bootstrap writes the same tags before Terraform runs.
  ci_tags = var.ci_git_ref == "" ? {} : merge(
    { ci_git_ref = var.ci_git_ref },
    var.ci_repository == "" ? {} : { ci_repository = var.ci_repository }
  )
}
