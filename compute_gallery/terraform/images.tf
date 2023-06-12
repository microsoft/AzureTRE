module "image" {
  source               = "./image"
  for_each             = local.images
  location             = azurerm_resource_group.compute_gallery.location
  resource_group_name  = azurerm_resource_group.compute_gallery.name  
  image_gallery_name   = azurerm_shared_image_gallery.sig.name
  storage_account_name = azurerm_storage_account.compute_gallery.name
  share_name           = azurerm_storage_share.compute_gallery.name
  share_url            = azurerm_storage_share.compute_gallery.url
  image_builder_id     = azurerm_user_assigned_identity.image_builder.id

  image_identifier = each.key
  image_definition = each.value.image_definition
  template_name    = each.value.template_name
  offer_name       = each.value.offer_name
  publisher_name   = each.value.publisher_name
  sku              = each.value.sku
  os_type          = each.value.os_type
  description      = each.value.description
  hyperv_version   = each.value.hyperv_version

}
