data "azurerm_storage_share" "shared_storage" {
  name                 = local.shared_storage_share
  storage_account_name = local.storage_name
}

data "template_file" "mlflow_windows_config" {
  template = file("${path.module}/../mlflow-vm-config/windows/template_config.ps1")
  vars = {
    MLFlow_Connection_String = data.azurerm_storage_account.mlflow.primary_connection_string
  }
}

data "template_file" "mlflow_linux_config" {
  template = file("${path.module}/../mlflow-vm-config/linux/template_config.sh")
  vars = {
    MLFlow_Connection_String = data.azurerm_storage_account.mlflow.primary_connection_string
  }
}

data "local_file" "version" {
  filename = "${path.module}/../mlflow-server/version.txt"
}

data "azurerm_monitor_diagnostic_categories" "mlflow" {
  resource_id = azurerm_linux_web_app.mlflow.id
  depends_on = [
    azurerm_linux_web_app.mlflow
  ]
}
