data "azuread_service_principal" "core_api" {
  client_id = var.core_api_client_id
}
