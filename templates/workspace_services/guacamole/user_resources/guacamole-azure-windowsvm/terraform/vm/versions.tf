# Shared Guacamole Windows VM module.
# This module contains the VM resources common to the standard Guacamole Windows
# VM and the airlock import/export review VMs. Provider configuration is supplied
# by the calling root module (no provider blocks here).
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.57.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.7.2"
    }
    time = {
      source  = "hashicorp/time"
      version = "0.13.1"
    }
  }
}
