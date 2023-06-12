resource "azapi_resource" "image_template" {
  type      = "Microsoft.VirtualMachineImages/imageTemplates@2020-02-14"
  name      = "template-${var.image_identifier}"
  parent_id = data.azurerm_resource_group.compute_gallery.id
  location  = var.location

  body = <<EOF
{
  "identity": {
      "type": "UserAssigned",
      "userAssignedIdentities": {
              "${var.image_builder_id}": {}
          }
  },
  "properties": {
      "buildTimeoutInMinutes" : 90,

      "vmProfile":
          {
          "vmSize": "Standard_DS2_v2",
          "osDiskSizeGB": 30
          },

      "source": {
          "type": "PlatformImage",
              "publisher": "canonical",
              "offer": "0001-com-ubuntu-server-jammy",
              "sku": "22_04-lts-gen2",
              "version": "latest"

      },
      "customize": [
        {
            "type": "File",
            "name": "VMInitScript",
            "sourceUri": "${var.share_url}/${azurerm_storage_share_directory.scripts.name}/init.sh",
            "destination":"/tmp/init.sh"
        },
        {
            "type": "Shell",
            "name": "setupVM",
            "inline": [
                "cd /tmp",
                "chmod +x init.sh",
                "sudo /tmp/init.sh"
            ]
        }
      ],
      "distribute": [
        {
            "type": "SharedImage",
            "galleryImageId": "${azurerm_shared_image.image.id}",
            "runOutputName": "${var.image_definition}",
            "artifactTags": {
                "source": "azureVmImageBuilder",
                "baseosimg": "ubuntu2204"
            },
            "replicationRegions": ["uksouth"],
            "storageAccountType": "Standard_LRS"
        }
      ]
  }
}
  EOF

  tags = {
    "useridentity" = "enabled"
  }
}
