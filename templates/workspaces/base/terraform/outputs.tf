output "workspace_resource_name_suffix" {
  value = local.workspace_resource_name_suffix
}

output "app_role_id_workspace_owner" {
  value = var.register_aad_application ? module.aad[0].app_role_workspace_owner_id : var.app_role_id_workspace_owner
}

output "app_role_id_workspace_researcher" {
  value = var.register_aad_application ? module.aad[0].app_role_workspace_researcher_id : var.app_role_id_workspace_researcher
}

output "client_id" {
  value = var.register_aad_application ? module.aad[0].client_id : var.client_id
}

output "sp_id" {
  value = var.register_aad_application ? module.aad[0].sp_id : var.sp_id
}
