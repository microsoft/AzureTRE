output "app_role_workspace_owner_id" {
  value = random_uuid.app_role_workspace_owner_id.result
}

output "app_role_workspace_researcher_id" {
  value = random_uuid.app_role_workspace_researcher_id.result
}

output "app_role_workspace_airlock_manager_id" {
  value = random_uuid.app_role_workspace_airlock_manager_id.result
}

output "client_id" {
  value = azuread_application.workspace.client_id
}

output "scope_id" {
  value = "api://${var.workspace_resource_name_suffix}"
}

output "sp_id" {
  value = azuread_service_principal.workspace.object_id
}

output "workspace_owners_group_id" {
  value = var.create_aad_groups ? azuread_group.workspace_owners[0].object_id : ""
}

output "workspace_researchers_group_id" {
  value = var.create_aad_groups ? azuread_group.workspace_researchers[0].object_id : ""
}

output "workspace_airlock_managers_group_id" {
  value = var.create_aad_groups ? azuread_group.workspace_airlock_managers[0].object_id : ""
}


