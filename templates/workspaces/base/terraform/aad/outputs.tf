output "app_role_workspace_owner_id" {
  value = random_uuid.app_role_workspace_owner_id.result
}

output "app_role_workspace_researcher_id" {
  value = random_uuid.app_role_workspace_researcher_id.result
}

output "client_id" {
  value = azuread_application.workspace.application_id
}

output "scope_id" {
  value = random_uuid.scope_id.result
}

output "sp_id" {
  value = azuread_service_principal.workspace.object_id
}
