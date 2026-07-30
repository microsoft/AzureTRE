output "workspace_resource_name_suffix" {
  value = local.workspace_resource_name_suffix
}

output "app_role_id_workspace_owner" {
  value = module.aad.app_role_workspace_owner_id
}

output "app_role_id_workspace_researcher" {
  value = module.aad.app_role_workspace_researcher_id
}

output "app_role_id_workspace_airlock_manager" {
  value = module.aad.app_role_workspace_airlock_manager_id
}

output "client_id" {
  value = module.aad.client_id
}

output "sp_id" {
  value = module.aad.sp_id
}

output "scope_id" {
  value = module.aad.scope_id
}

output "backup_vault_name" {
  value = var.enable_backup ? module.backup[0].vault_name : ""
}

output "vm_backup_policy_id" {
  value = var.enable_backup ? module.backup[0].vm_backup_policy_id : ""
}

output "fileshare_backup_policy_id" {
  value = var.enable_backup ? module.backup[0].fileshare_backup_policy_id : ""
}

output "log_analytics_workspace_name" {
  value = module.azure_monitor.log_analytics_workspace_name
}

output "workspace_owners_group_id" {
  value = module.aad.workspace_owners_group_id
}

output "workspace_researchers_group_id" {
  value = module.aad.workspace_researchers_group_id
}

output "workspace_airlock_managers_group_id" {
  value = module.aad.workspace_airlock_managers_group_id
}
