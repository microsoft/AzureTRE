resource "azurerm_resource_group" "compute_gallery" {
  name     = "rg-cg-${var.tre_id}"
  location = var.location
  tags = {
    project = "Azure Trusted Research Environment"
    tre_id  = var.tre_id
    source  = "https://github.com/UCL-ARC/ARC-AzureTRE"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_user_assigned_identity" "image_builder" {
  name                = "id-image-builder-${var.tre_id}"
  location            = azurerm_resource_group.compute_gallery.location
  resource_group_name = azurerm_resource_group.compute_gallery.name
}

resource "azurerm_shared_image_gallery" "sig" {
  name                = "sig${var.tre_id}"
  location            = azurerm_resource_group.compute_gallery.location
  resource_group_name = azurerm_resource_group.compute_gallery.name
  description         = "Shared images"
}
