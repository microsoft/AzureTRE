resource "azurerm_log_analytics_query_pack" "tre" {
  name                = "querypack-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_log_analytics_query_pack_query" "rp_logs" {
  query_pack_id  = azurerm_log_analytics_query_pack.tre.id
  display_name   = "TRE Resource Processor Logs"
  resource_types = ["microsoft.insights/components"] // makes it visible in appinsights
  body           = <<EOT
traces
| where cloud_RoleName == "resource_processor"
| where message !in ("Looking for new session...", "No sessions for this process. Will look again...")
| project timestamp, message, severityLevel, itemType, operation_Id, operation_ParentId, customDimensions
| union (
exceptions
| where cloud_RoleName == "resource_processor"
| project timestamp, problemId, severityLevel, itemType, type, method, outerType, outerMessage, outerMethod, ['details'], customDimensions, operation_Id, operation_ParentId
)
| order by timestamp desc
EOT
}

resource "azurerm_log_analytics_query_pack_query" "api_logs" {
  query_pack_id  = azurerm_log_analytics_query_pack.tre.id
  display_name   = "TRE API Logs"
  resource_types = ["microsoft.insights/components"] // makes it visible in appinsights
  body           = <<EOT
traces
| where cloud_RoleName == "api"
| where message !in ("Looking for new session...")
| where message !startswith ("AMQP error occurred:")
| where customDimensions.fileName !startswith "/usr/local/lib/python3.8/site-packages/azure/servicebus/aio"
| where message !startswith "Unclosed client session"
| project timestamp, message, severityLevel, itemType, operation_Id, operation_ParentId, customDimensions
| union (
exceptions
| where cloud_RoleName == "api"
| project timestamp, problemId, severityLevel, itemType, type, method, outerType, outerMessage, outerMethod, ['details'], customDimensions, operation_Id, operation_ParentId
)
| order by timestamp desc
EOT
}
