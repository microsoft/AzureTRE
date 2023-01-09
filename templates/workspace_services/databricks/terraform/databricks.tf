resource "azurerm_databricks_workspace" "databricks" {
  name                              = local.databricks_workspace_name
  resource_group_name               = data.azurerm_resource_group.rg.name
  location                          = data.azurerm_resource_group.rg.location
  sku                               = "premium"
  managed_resource_group_name       = local.managed_resource_group_name
  infrastructure_encryption_enabled = true

  tags = local.tre_workspace_service_tags
  lifecycle { ignore_changes = [tags] }

  custom_parameters {
    no_public_ip        = true
    public_subnet_name  = azurerm_subnet.public.name
    private_subnet_name = azurerm_subnet.private.name
    virtual_network_id  = data.azurerm_virtual_network.ws.id

    public_subnet_network_security_group_association_id  = azurerm_subnet_network_security_group_association.public.id
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.private.id
  }
}



# resource "databricks_workspace_conf" "databricks-ws" {
#   custom_config = {
#     "enableIpAccessLists" : true
#   }
#   depends_on = [azurerm_databricks_workspace.databricks]
# }

# resource "databricks_ip_access_list" "allowed-list" {
#   label     = "allow_in"
#   list_type = "ALLOW"
#   ip_addresses = [
#     "${data.azurerm_public_ip.firewall-public-ip.ip_address}/32",
#     "${chomp(data.http.myip.response_body)}/32"
#   ]
#   depends_on = [databricks_workspace_conf.databricks-ws]
# }


# data "azuread_group" "aad-admin-group" {
#   display_name     = var.admin_group
#   security_enabled = true
# }
# data "azuread_users" "aad-admin-users" {
#   object_ids = data.azuread_group.aad-admin-group.members
# }

# resource "databricks_user" "adb-admin-user" {
#     for_each = { for i,v in data.azuread_users.workspace_owners.users: i=>v }
#       user_name     = each.value.mail
#       display_name  = each.value.display_name
#       allow_cluster_create = true
# }

# resource "databricks_user" "adb-user" {
#     for_each = { for i,v in data.azuread_users.workspace_users.users: i=>v }
#       user_name     = each.value.mail
#       display_name  = each.value.display_name
#       allow_cluster_create = false
# }
