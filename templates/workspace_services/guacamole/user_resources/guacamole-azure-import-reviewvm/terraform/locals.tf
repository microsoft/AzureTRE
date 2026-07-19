locals {
  nexus_proxy_url = "https://nexus-${data.azurerm_public_ip.app_gateway_ip.fqdn}"

  # Load VM SKU/image details from porter.yaml
  porter_yaml   = yamldecode(file("${path.module}/../porter.yaml"))
  vm_sizes      = local.porter_yaml["custom"]["vm_sizes"]
  image_details = local.porter_yaml["custom"]["image_options"]

  # Airlock-specific: download the in-progress review data onto the VM.
  review_data_script = templatefile("${path.module}/download_review_data.ps1", {
    airlock_request_sas_url = var.airlock_request_sas_url
  })
}
