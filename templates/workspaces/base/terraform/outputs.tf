output "workspace_resource_name_suffix" {
  value = local.workspace_resource_name_suffix
}

# The following outputs are dependent on an Automatic AAD Workspace Application Registration.
# If we are not creating an App Reg we simple pass back the same values that were already created
# This is necessary so that we don't delete workspace properties
output "app_role_id_workspace_owner" {
  value = var.register_aad_application ? module.aad[0].app_role_workspace_owner_id : var.app_role_id_workspace_owner
}

output "app_role_id_workspace_researcher" {
  value = var.register_aad_application ? module.aad[0].app_role_workspace_researcher_id : var.app_role_id_workspace_researcher
}

output "app_role_id_workspace_airlock_manager" {
  value = var.register_aad_application ? module.aad[0].app_role_workspace_airlock_manager_id : var.app_role_id_workspace_airlock_manager
}

output "client_id" {
  value = var.register_aad_application ? module.aad[0].client_id : var.client_id
}

output "sp_id" {
  value = var.register_aad_application ? module.aad[0].sp_id : var.sp_id
}

output "scope_id" {
  value = var.register_aad_application ? module.aad[0].scope_id : var.scope_id
}

output "workspace_owners_group_id" {
  value = var.register_aad_application ? module.aad[0].workspace_owners_group_id : ""
}

output "workspace_researchers_group_id" {
  value = var.register_aad_application ? module.aad[0].workspace_researchers_group_id : ""
}

output "workspace_airlock_managers_group_id" {
  value = var.register_aad_application ? module.aad[0].workspace_airlock_managers_group_id : ""
}
