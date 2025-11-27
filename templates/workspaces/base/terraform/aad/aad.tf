data "azuread_client_config" "current" {}

data "azuread_service_principal" "ui" {
  client_id = var.ui_client_id
}

resource "random_uuid" "oauth2_user_impersonation_id" {}
resource "random_uuid" "app_role_workspace_owner_id" {}
resource "random_uuid" "app_role_workspace_researcher_id" {}
resource "random_uuid" "app_role_workspace_airlock_manager_id" {}

locals {
  workspace_sp_password_rotation_days        = 30
  workspace_sp_password_validity_days        = 180
  workspace_sp_password_rotation_offset_days = 15
}

resource "time_rotating" "workspace_sp_password_primary" {
  rotation_days = local.workspace_sp_password_rotation_days
}

resource "time_rotating" "workspace_sp_password_secondary" {
  rotation_days = local.workspace_sp_password_rotation_days
  rfc3339       = timeadd(time_rotating.workspace_sp_password_primary.rotation_rfc3339, "${local.workspace_sp_password_rotation_offset_days * 24}h")
}

resource "azuread_application" "workspace" {
  display_name    = var.workspace_resource_name_suffix
  identifier_uris = ["api://${var.workspace_resource_name_suffix}"]
  owners          = [data.azuread_client_config.current.object_id, data.azuread_service_principal.core_api.object_id]

  api {
    mapped_claims_enabled          = true
    requested_access_token_version = 2

    oauth2_permission_scope {
      admin_consent_description  = "Allow the app to access the Workspace API on behalf of the signed-in user."
      admin_consent_display_name = "Access the Workspace API on behalf of signed-in user"
      enabled                    = true
      id                         = random_uuid.oauth2_user_impersonation_id.result
      type                       = "User"
      user_consent_description   = "Allow the app to access the Workspace API on your behalf."
      user_consent_display_name  = "Access the Workspace API"
      value                      = "user_impersonation"
    }
  }

  app_role {
    allowed_member_types = ["User", "Application"]
    description          = "Provides workspace owners access to the Workspace."
    display_name         = "Workspace Owner"
    enabled              = true
    id                   = random_uuid.app_role_workspace_owner_id.result
    value                = "WorkspaceOwner"
  }

  app_role {
    allowed_member_types = ["User", "Application"]
    description          = "Provides researchers access to the Workspace."
    display_name         = "Workspace Researcher"
    enabled              = true
    id                   = random_uuid.app_role_workspace_researcher_id.result
    value                = "WorkspaceResearcher"
  }

  app_role {
    allowed_member_types = ["User", "Application"]
    description          = "Provides airlock managers access to the Workspace and ability to review airlock requests."
    display_name         = "Airlock Manager"
    enabled              = true
    id                   = random_uuid.app_role_workspace_airlock_manager_id.result
    value                = "AirlockManager"
  }

  feature_tags {
    enterprise = true
  }

  optional_claims {
    id_token {
      name      = "ipaddr"
      essential = false
    }

    id_token {
      name      = "email"
      essential = false
    }
  }

  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph

    resource_access {
      id   = "64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0" # Email
      type = "Scope"                                # Delegated
    }
    resource_access {
      id   = "37f7f235-527c-4136-accd-4a02d197296e" # Openid
      type = "Scope"                                # Delegated
    }
    resource_access {
      id   = "14dad69e-099b-42c9-810b-d002981feec1" # Profile
      type = "Scope"                                # Delegated
    }
  }

  web {
    redirect_uris = jsondecode(base64decode(var.aad_redirect_uris_b64))[*].value
  }
}

resource "azuread_service_principal" "workspace" {
  client_id                    = azuread_application.workspace.client_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id, var.workspace_owner_object_id, data.azuread_service_principal.core_api.object_id]

  feature_tags {
    enterprise = true
  }
}

resource "azuread_service_principal_delegated_permission_grant" "ui" {
  count                                = var.auto_grant_workspace_consent ? 1 : 0
  service_principal_object_id          = data.azuread_service_principal.ui.object_id
  resource_service_principal_object_id = azuread_service_principal.workspace.object_id
  claim_values                         = ["user_impersonation"]
}

resource "azuread_application_password" "workspace_primary" {
  application_id = azuread_application.workspace.id
  display_name   = "Primary Password"
  end_date = timeadd(
    time_rotating.workspace_sp_password_primary.rotation_rfc3339,
    format("%dh", local.workspace_sp_password_validity_days * 24)
  )

  rotate_when_changed = {
    rotation = time_rotating.workspace_sp_password_primary.rotation_rfc3339
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "azuread_application_password" "workspace_secondary" {
  application_id = azuread_application.workspace.id
  display_name   = "Secondary Password"
  end_date = timeadd(
    time_rotating.workspace_sp_password_secondary.rotation_rfc3339,
    format("%dh", local.workspace_sp_password_validity_days * 24)
  )

  rotate_when_changed = {
    rotation = time_rotating.workspace_sp_password_secondary.rotation_rfc3339
  }

  lifecycle {
    create_before_destroy = true
  }
}

locals {
  # Use timecmp function to compare timestamps
  # timecmp returns 1 if first timestamp is later, -1 if earlier, 0 if equal
  primary_is_newer = timecmp(time_rotating.workspace_sp_password_primary.rotation_rfc3339, time_rotating.workspace_sp_password_secondary.rotation_rfc3339) > 0

  # Use the newer password as the current password
  current_password = local.primary_is_newer ? azuread_application_password.workspace_primary.value : azuread_application_password.workspace_secondary.value
}

resource "azurerm_key_vault_secret" "client_id" {
  name         = "workspace-client-id"
  value        = azuread_application.workspace.client_id
  key_vault_id = var.key_vault_id
  tags         = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "client_secret" {
  name         = "workspace-client-secret"
  value        = local.current_password
  key_vault_id = var.key_vault_id
  tags         = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azuread_app_role_assignment" "workspace_owner" {
  app_role_id         = azuread_application.workspace.app_role_ids["WorkspaceOwner"]
  principal_object_id = var.workspace_owner_object_id
  resource_object_id  = azuread_service_principal.workspace.object_id
}

resource "azuread_group" "workspace_owners" {
  count            = var.create_aad_groups ? 1 : 0
  display_name     = "${var.workspace_resource_name_suffix} Workspace Owners"
  owners           = [var.workspace_owner_object_id, data.azuread_service_principal.core_api.object_id, data.azuread_client_config.current.object_id]
  security_enabled = true
}

resource "azuread_group" "workspace_researchers" {
  count            = var.create_aad_groups ? 1 : 0
  display_name     = "${var.workspace_resource_name_suffix} Workspace Researchers"
  owners           = [var.workspace_owner_object_id, data.azuread_service_principal.core_api.object_id, data.azuread_client_config.current.object_id]
  security_enabled = true
}

resource "azuread_group" "workspace_airlock_managers" {
  count            = var.create_aad_groups ? 1 : 0
  display_name     = "${var.workspace_resource_name_suffix} Airlock Managers"
  owners           = [var.workspace_owner_object_id, data.azuread_service_principal.core_api.object_id, data.azuread_client_config.current.object_id]
  security_enabled = true
}

resource "azuread_group_member" "workspace_owner" {
  count            = var.create_aad_groups ? 1 : 0
  group_object_id  = azuread_group.workspace_owners[count.index].object_id
  member_object_id = var.workspace_owner_object_id
}

resource "azuread_app_role_assignment" "workspace_owners_group" {
  count               = var.create_aad_groups ? 1 : 0
  app_role_id         = azuread_application.workspace.app_role_ids["WorkspaceOwner"]
  principal_object_id = azuread_group.workspace_owners[count.index].object_id
  resource_object_id  = azuread_service_principal.workspace.object_id
}

resource "azuread_app_role_assignment" "workspace_researchers_group" {
  count               = var.create_aad_groups ? 1 : 0
  app_role_id         = azuread_application.workspace.app_role_ids["WorkspaceResearcher"]
  principal_object_id = azuread_group.workspace_researchers[count.index].object_id
  resource_object_id  = azuread_service_principal.workspace.object_id
}

resource "azuread_app_role_assignment" "workspace_airlock_managers_group" {
  count               = var.create_aad_groups ? 1 : 0
  app_role_id         = azuread_application.workspace.app_role_ids["AirlockManager"]
  principal_object_id = azuread_group.workspace_airlock_managers[count.index].object_id
  resource_object_id  = azuread_service_principal.workspace.object_id
}
