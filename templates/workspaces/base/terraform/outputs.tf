output "workspace_resource_name_suffix" {
  value = local.workspace_resource_name_suffix
}

output "WorkspaceOwnerAppRoleId" {
  value = var.register_aad_application ? module.aad[0].app_role_workspace_owner_id : ""
}

output "WorkspaceResearcherAppRoleId" {
  value = var.register_aad_application ? module.aad[0].app_role_workspace_researcher_id : ""
}

output "client_id" {
  value = var.register_aad_application ? module.aad[0].client_id : ""
}

output "sp_id" {
  value = var.register_aad_application ? module.aad[0].sp_id : ""
}
