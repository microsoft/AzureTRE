data "azurerm_firewall" "fw" {
  name                = "fw-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

locals {
  allowed_inner_eye_urls = ["*.anaconda.com", "*.anaconda.org", "binstar-cio-packages-prod.s3.amazonaws.com", "*pythonhosted.org", "github-cloud.githubusercontent.com", "azure.archive.ubuntu.com", "packagecloud.io"]
}

data "azurerm_client_config" "current" {}
resource "null_resource" "az_login_sp" {

  count = var.arm_use_msi == true ? 0 : 1
  provisioner "local-exec" {
    command = "az login --service-principal --username ${var.arm_client_id} --password ${var.arm_client_secret} --tenant ${var.arm_tenant_id}"
  }

  triggers = {
    timestamp = timestamp()
  }

}

resource "null_resource" "az_login_msi" {

  count = var.arm_use_msi == true ? 1 : 0
  provisioner "local-exec" {
    command = "az login --identity -u '${data.azurerm_client_config.current.client_id}'"
  }

  triggers = {
    timestamp = timestamp()
  }
}

data "external" "rule_priorities" {
  program = ["bash", "-c", "./get_firewall_priorities.sh"]

  query = {
    firewall_name          = data.azurerm_firewall.fw.name
    resource_group_name    = data.azurerm_firewall.fw.resource_group_name
    collection_name_suffix = "${local.service_resource_name_suffix}-aml"
  }
  depends_on = [
    null_resource.az_login_sp,
    null_resource.az_login_msi
  ]
}

resource "azurerm_firewall_application_rule_collection" "innereyeapprulecollection" {
  name                = "arc-${local.service_resource_name_suffix}-aml"
  azure_firewall_name = data.azurerm_firewall.fw.name
  resource_group_name = data.azurerm_firewall.fw.resource_group_name
  priority            = data.external.rule_priorities.result.application_rule_priority
  action              = "Allow"

  rule {
    name = "allowInnerEyerelated"

    source_addresses = data.azurerm_virtual_network.ws.address_space

    target_fqdns = local.allowed_inner_eye_urls


    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }
  }
}
