removed {
  from = azurerm_role_assignment.resource_processor_avd_artifacts

  lifecycle {
    destroy = false
  }
}

resource "terraform_data" "resource_processor_avd_artifacts" {
  triggers_replace = uuidv5("url", "${data.azurerm_storage_account.stg.id}/Storage Blob Data Contributor/${data.azurerm_user_assigned_identity.resource_processor_vmss_id.principal_id}")

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      token_response=$(curl --fail --silent --show-error -H Metadata:true "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fmanagement.azure.com%2F&client_id=${data.azurerm_user_assigned_identity.resource_processor_vmss_id.client_id}")
      access_token=$(printf '%s' "$token_response" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
      test -n "$access_token"
      curl --fail-with-body --silent --show-error --retry 18 --retry-delay 10 --retry-all-errors \
        --request PUT \
        --header "Authorization: Bearer $access_token" \
        --header "Content-Type: application/json" \
        --data '{"properties":{"roleDefinitionId":"/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/ba92f5b4-2d11-453d-a403-e96b0029c9fe","principalId":"${data.azurerm_user_assigned_identity.resource_processor_vmss_id.principal_id}","principalType":"ServicePrincipal"}}' \
        "https://management.azure.com${data.azurerm_storage_account.stg.id}/providers/Microsoft.Authorization/roleAssignments/${uuidv5("url", "${data.azurerm_storage_account.stg.id}/Storage Blob Data Contributor/${data.azurerm_user_assigned_identity.resource_processor_vmss_id.principal_id}")}?api-version=2022-04-01"
    EOT
  }
}

resource "azurerm_storage_container" "avd_artifacts" {
  count = var.host_pool_type == "Pooled" ? 1 : 0

  name                  = "avd-${local.short_service_id}"
  storage_account_id    = data.azurerm_storage_account.stg.id
  container_access_type = "private"

  depends_on = [terraform_data.resource_processor_avd_artifacts]
}

removed {
  from = azurerm_storage_blob.avd_dsc

  lifecycle {
    destroy = false
  }
}

resource "terraform_data" "avd_dsc" {
  count = var.host_pool_type == "Pooled" ? 1 : 0

  triggers_replace = [local.avd_dsc_artifact_sha256, local.avd_dsc_artifact_url]

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      token_response=$(curl --fail --silent --show-error -H Metadata:true "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fstorage.azure.com%2F&client_id=${data.azurerm_user_assigned_identity.resource_processor_vmss_id.client_id}")
      access_token=$(printf '%s' "$token_response" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
      test -n "$access_token"
      curl --fail-with-body --silent --show-error --retry 18 --retry-delay 10 --retry-all-errors \
        --request PUT \
        --header "Authorization: Bearer $access_token" \
        --header "x-ms-version: 2023-11-03" \
        --header "x-ms-date: $(LC_ALL=C date -u '+%a, %d %b %Y %H:%M:%S GMT')" \
        --header "x-ms-blob-type: BlockBlob" \
        --upload-file "${path.module}/../Configuration.zip" \
        "${data.azurerm_storage_account.stg.primary_blob_endpoint}${azurerm_storage_container.avd_artifacts[0].name}/Configuration.zip"
    EOT
  }

  depends_on = [terraform_data.resource_processor_avd_artifacts]
}

resource "azurerm_network_interface" "pooled_session_host" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  name                = "nic-avdsh-${local.short_service_id}-${count.index + 1}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  tags                = local.workspace_service_tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = data.azurerm_subnet.services.id
    private_ip_address_allocation = "Dynamic"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "random_password" "pooled_session_host" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  length           = 16
  min_lower        = 1
  min_upper        = 1
  min_numeric      = 1
  min_special      = 1
  override_special = "_%@"
}

resource "azurerm_windows_virtual_machine" "pooled_session_host" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  name                       = "${local.session_host_name_prefix}${count.index + 1}"
  location                   = data.azurerm_resource_group.ws.location
  resource_group_name        = data.azurerm_resource_group.ws.name
  network_interface_ids      = [azurerm_network_interface.pooled_session_host[count.index].id]
  size                       = var.pooled_vm_size
  allow_extension_operations = true
  admin_username             = "avdadmin"
  admin_password             = random_password.pooled_session_host[count.index].result
  encryption_at_host_enabled = true
  secure_boot_enabled        = true
  vtpm_enabled               = true
  license_type               = "Windows_Client"
  tags                       = local.workspace_service_tags

  source_image_reference {
    publisher = "microsoftwindowsdesktop"
    offer     = "windows-11"
    sku       = "win11-24h2-avd"
    version   = "latest"
  }

  os_disk {
    name                 = "osdisk-${local.session_host_name_prefix}${count.index + 1}"
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
  }

  identity {
    type = "SystemAssigned"
  }

  lifecycle { ignore_changes = [tags, os_disk[0].storage_account_type] }
}

resource "azurerm_role_assignment" "pooled_session_host_login" {
  for_each = {
    for pair in setproduct(range(var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0), local.workspace_role_principal_ids) :
    "${pair[0]}:${pair[1]}" => { host_index = pair[0], principal_id = pair[1] }
  }

  scope                = azurerm_windows_virtual_machine.pooled_session_host[each.value.host_index].id
  role_definition_name = "Virtual Machine User Login"
  principal_id         = each.value.principal_id
}

resource "azurerm_role_assignment" "pooled_session_host_power_on" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  scope                = azurerm_windows_virtual_machine.pooled_session_host[count.index].id
  role_definition_name = "Desktop Virtualization Power On Contributor"
  principal_id         = data.azuread_service_principal.avd[0].object_id
}

resource "azurerm_role_assignment" "pooled_session_host_avd_artifact_reader" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  scope                = "${data.azurerm_storage_account.stg.id}/blobServices/default/containers/${azurerm_storage_container.avd_artifacts[0].name}"
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_windows_virtual_machine.pooled_session_host[count.index].identity[0].principal_id
}

resource "azurerm_virtual_machine_run_command" "prepare_pooled_session_host" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  name               = "prepare-avd-session-host"
  location           = data.azurerm_resource_group.ws.location
  virtual_machine_id = azurerm_windows_virtual_machine.pooled_session_host[count.index].id

  source {
    script = templatefile("${path.module}/prepare_session_host.ps1.tftpl", {
      clipboard_server_to_client = local.clipboard_server_to_client
      clipboard_client_to_server = local.clipboard_client_to_server
    })
  }
}

resource "azapi_resource_action" "restart_pooled_session_host" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  type        = "Microsoft.Compute/virtualMachines@2024-07-01"
  resource_id = azurerm_windows_virtual_machine.pooled_session_host[count.index].id
  action      = "restart"

  depends_on = [azurerm_virtual_machine_run_command.prepare_pooled_session_host]
  lifecycle {
    replace_triggered_by = [azurerm_virtual_machine_run_command.prepare_pooled_session_host[count.index]]
  }
}

resource "azurerm_virtual_machine_extension" "pooled_avd_dsc" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  name                       = "configure-avd-session-host"
  virtual_machine_id         = azurerm_windows_virtual_machine.pooled_session_host[count.index].id
  publisher                  = "Microsoft.Compute"
  type                       = "CustomScriptExtension"
  type_handler_version       = "1.10"
  auto_upgrade_minor_version = true
  tags                       = local.workspace_service_tags

  protected_settings = jsonencode({
    commandToExecute = "powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand ${textencodebase64(templatefile("${path.module}/configure_session_host.ps1.tftpl", {
      artifact_url               = local.avd_dsc_artifact_url
      artifact_sha256            = local.avd_dsc_artifact_sha256
      host_pool_name             = azurerm_virtual_desktop_host_pool.avd.name
      registration_token         = data.azurerm_key_vault_secret.avd_registration_token.value
      clipboard_server_to_client = local.clipboard_server_to_client
      clipboard_client_to_server = local.clipboard_client_to_server
      mount_storage_command      = ""
    }), "UTF-16LE")}"
  })

  depends_on = [
    azapi_resource_action.restart_pooled_session_host,
    azurerm_role_assignment.pooled_session_host_avd_artifact_reader,
    terraform_data.avd_dsc,
    azurerm_private_endpoint.hostpool,
    azurerm_private_endpoint.workspace,
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_virtual_machine_extension" "pooled_aad_join" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  name                       = "AADLoginForWindows"
  virtual_machine_id         = azurerm_windows_virtual_machine.pooled_session_host[count.index].id
  publisher                  = "Microsoft.Azure.ActiveDirectory"
  type                       = "AADLoginForWindows"
  type_handler_version       = "2.2"
  auto_upgrade_minor_version = true
  tags                       = local.workspace_service_tags

  depends_on = [azurerm_virtual_machine_extension.pooled_avd_dsc]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "pooled_session_host_credentials" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  name         = "${local.session_host_name_prefix}${count.index + 1}-admin-credentials"
  value        = "avdadmin\n${random_password.pooled_session_host[count.index].result}"
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azapi_resource_action" "unregister_pooled_session_host" {
  count = var.host_pool_type == "Pooled" ? var.pooled_session_host_count : 0

  type             = "Microsoft.DesktopVirtualization/hostPools/sessionHosts@2024-04-03"
  resource_id      = "${azurerm_virtual_desktop_host_pool.avd.id}/sessionHosts/${azurerm_windows_virtual_machine.pooled_session_host[count.index].name}"
  method           = "DELETE"
  when             = "destroy"
  ignore_not_found = true
  query_parameters = { force = ["true"] }

  depends_on = [azurerm_virtual_machine_extension.pooled_aad_join]

  lifecycle {
    replace_triggered_by = [azurerm_windows_virtual_machine.pooled_session_host[count.index].virtual_machine_id]
  }
}