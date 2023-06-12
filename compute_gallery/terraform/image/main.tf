resource "azurerm_shared_image" "image" {
  name                = var.image_definition
  gallery_name        = var.image_gallery_name
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = var.os_type
  description         = var.description
  hyper_v_generation  = var.hyperv_version

  identifier {
    publisher = var.publisher_name
    offer     = var.offer_name
    sku       = var.sku
  }
}
