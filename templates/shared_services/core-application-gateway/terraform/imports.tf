# TODO: uncomment when we use Terraform 1.5+

# data "azurerm_subscription" "current" {
# }

# import {
#   to = azurerm_application_gateway.agw
#   id = "/subscriptions/${data.azurerm_subscription.current.subscription_id}/resourceGroups/${local.core_resource_group_name}/providers/Microsoft.Network/applicationGateways/agw-${var.tre_id}"
# }
