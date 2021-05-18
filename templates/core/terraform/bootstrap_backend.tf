terraform {
  backend "azurerm" {
    resource_group_name  = "tmptfstate"
    storage_account_name = "marcus1805"
    container_name       = "tfstate"
    key                  = "tmp6dev"
  }
}
