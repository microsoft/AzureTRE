data "azurerm_firewall" "fw" {
  name                = "fw-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}


locals {
  allowedInnerEyeURLs           = ["*.anaconda.com", "*.anaconda.org", "binstar-cio-packages-prod.s3.amazonaws.com", "github.com", "*pypi.org", "*pythonhosted.org", "github-cloud.githubusercontent.com"]
}

resource "null_resource" "az_login" {
  provisioner "local-exec" {
    command = "az login --service-principal -u '${var.arm_client_id}' -p '${var.arm_client_secret}' --tenant '${var.arm_tenant_id}'"
  }

  triggers = {
    timestamp = timestamp()
  }
}

data "external" "rule_priorities" {
  program = ["bash", "-c", "./get_firewall_priorities.sh"]

  query = {
    firewall_name       = data.azurerm_firewall.fw.name
    resource_group_name = data.azurerm_firewall.fw.resource_group_name
    service_resource_name_suffix = local.service_resource_name_suffix
  }
  depends_on = [
    null_resource.az_login
  ]
}


resource "azurerm_firewall_application_rule_collection" "innereyeapprulecollection" {
  name                = "arc-${local.service_resource_name_suffix}"
  azure_firewall_name = data.azurerm_firewall.fw.name
  resource_group_name = data.azurerm_firewall.fw.resource_group_name
  priority            = data.external.rule_priorities.result.application_rule_priority
  action              = "Allow"

  rule {
    name = "allowInnerEyerelated"

    source_addresses = data.azurerm_virtual_network.ws.address_space

    target_fqdns = local.allowedInnerEyeURLs


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
