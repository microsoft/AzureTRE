resource "azurerm_role_definition" "image_builder" {
  name        = "role-image-builder-${var.tre_id}"
  scope       = data.azurerm_subscription.current.id
  description = "Role for the image builder to read/wrote images"

  permissions {
    actions = [
      "Microsoft.Compute/galleries/read",
      "Microsoft.Compute/galleries/images/read",
      "Microsoft.Compute/galleries/images/versions/read",
      "Microsoft.Compute/galleries/images/versions/write",

      "Microsoft.Compute/images/write",
      "Microsoft.Compute/images/read",
      "Microsoft.Compute/images/delete"
    ]
  }

  assignable_scopes = [
    data.azurerm_subscription.current.id
  ]
}

resource "azurerm_role_assignment" "builder_can_read_writh_images" {
  principal_id       = azurerm_user_assigned_identity.image_builder.principal_id
  scope              = azurerm_resource_group.compute_gallery.id
  role_definition_id = azurerm_role_definition.image_builder.role_definition_resource_id
}

resource "azurerm_role_assignment" "builder_can_read_storage" {
  principal_id         = azurerm_user_assigned_identity.image_builder.principal_id
  scope                = azurerm_storage_account.compute_gallery.id
  role_definition_name = "Storage File Data Privileged Reader"
}
