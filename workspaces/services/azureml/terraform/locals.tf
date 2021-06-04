# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

locals {
  service_id                   = random_string.unique_id.result
  service_resource_name_suffix = "${var.tre_id}-ws-${var.workspace_id}-svc-${local.service_id}"
  allowed_urls                 = ["graph.windows.net", "ml.azure.com", "login.microsoftonline.com", "aadcdn.msftauth.net", "*privatelink.api.azureml.ms", "graph.microsoft.com", "management.azure.com", "*privatelink.file.core.windows.net", "*privatelink.vaultcore.azure.net", "*privatelink.notebooks.azure.net", "*privatelink.azurecr.io", "*privatelink.blob.core.windows.net", "viennaglobal.azurecr.io"]
  allowed_service_tags         = ["Storage.WestEurope", "AzureContainerRegistry"]

  workspace_name = lower("ml-${substr(local.service_resource_name_suffix, -30, -1)}")
}
