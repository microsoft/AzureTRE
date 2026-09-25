locals {
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  ws_resource_group_name         = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))

  admin_username = (
    var.admin_username == "" ?
    (length(data.azuread_user.user[0].mail) > 0 && strcontains(data.azuread_user.user[0].user_principal_name, "#EXT#") ?
      substr(element(split("@", data.azuread_user.user[0].mail), 0), 0, 20) :
      substr(element(split("#EXT#", element(split("@", data.azuread_user.user[0].user_principal_name), 0)), 0), 0, 20)
    ) :
    var.admin_username
  )

  nexus_proxy_url = "https://nexus-${data.azurerm_public_ip.app_gateway_ip.fqdn}"

  # Load VM SKU/image details from porter.yaml
  porter_yaml   = yamldecode(file("${path.module}/../porter.yaml"))
  vm_sizes      = local.porter_yaml["custom"]["vm_sizes"]
  image_details = local.porter_yaml["custom"]["image_options"]
}
