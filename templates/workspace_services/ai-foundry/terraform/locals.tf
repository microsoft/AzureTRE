locals {
  workspace_subscription_id      = coalesce(var.workspace_subscription_id, data.azurerm_client_config.current.subscription_id)
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  core_resource_group_name       = "rg-${var.tre_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")

  workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }

  # Split the OpenAI model value into its name and version.
  openai_model = {
    name    = trimspace(split("|", var.openai_model)[0])
    version = trimspace(split("|", var.openai_model)[1])
  }

  # The account catalogue can list a model after its Standard pricing tier has
  # expired. Match the exact model name and version. Require a model that is
  # generally available, supports chat, and does not use fine-tuning. If its
  # deprecation date has passed, reject the model.
  selected_openai_catalog_models = [
    for model in try(data.azapi_resource_action.available_models.output.value, []) : model
    if try(model.format, "") == "OpenAI"
    && try(model.name, "") == local.openai_model.name
    && try(model.version, "") == local.openai_model.version
  ]

  selected_openai_model_is_deployable = anytrue([
    for model in local.selected_openai_catalog_models :
    try(model.lifecycleStatus, "") == "GenerallyAvailable"
    && try(model.capabilities.chatCompletion, "false") == "true"
    && anytrue([
      for sku in try(model.skus, []) :
      try(sku.name, "") == "Standard"
      && !strcontains(lower(try(sku.usageName, "")), "finetune")
      && (
        try(sku.deprecationDate, null) == null
        ? true
        : try(timecmp(plantimestamp(), sku.deprecationDate) < 0, false)
      )
    ])
  ])

}
