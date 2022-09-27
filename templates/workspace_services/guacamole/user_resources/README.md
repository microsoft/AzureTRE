# Guacamole User Resources

This folder contains user resources that can be deployed with the Guacamole workspace service:

- linuxvm - a Linux-based virtual machine (expects an Ubuntu 18.04-based VM)
- windowsvm - A Windows-based virtual machine


## Customising the user resources

The `guacamole-azure-linuxvm` and `guacamole-azure-windowsvm` folders follow a consistent layout.
To create a template To update one of these templates (or to create a new template based on these folders) to use different image details or VM sizes, there are a few files that need to be updated:

| File                           | Description                                                                                                                                                                                   |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `porter.yaml`                  | This file describes the template and the name should be updated when creating a template based on the folder.<br> Additionally, the version needs  to be updated to deploy an updated version |
| `template_schema.json`         | This file controls the validation applied to the template, for example specifying the valid options for fields such as size and image                                                         |
| `terraform/vm_sizes.json`      | This file provides the mapping from the size options listed in `template_schema.json` and the corresponding Azure VM SKU                                                                      |
| `terraform/image_details.json` | This file provides the mapping from the VM option listed in `template_schema.json` and the corresponding VM imageZ                                                                            |

### Image details

In `terraform/imges_details.json`, each image that can be used is set as a property on the root object:

```json
{
  "Ubuntu 18.04": {
    "source_image_reference": {
      "publisher": "canonical",
      "offer": "ubuntuserver",
      "sku": "18_04-lts-gen2",
      "version": "latest"
    },
    "install_ui": true,
    "conda_config": false
  },
  "Custom Image From Gallery": {
    "source_image_name": "my-custom-image",
    "install_ui": true,
    "conda_config": true
  }
}
```

The name of the image used here needs to be included in the corresponding enum in `template_schema.json`.

Within the image definition in `images_details.json` there are a few properties that can be specified:


| Name                     | Description                                                                                              |
| ------------------------ | -------------------------------------------------------------------------------------------------------- |
| `source_image_name`      | Specify VM image to use by name (see notes below for identifying the image gallery containing the image) |
| `source_image_reference` | Specify VM image to use by `publisher`, `offer`, `sku` & `version` (e.g. for Azure Marketplace images)   |
| `install_ui`             | (Linux only) Set `true` to install desktop environment                                                   |
| `conda_config`           | Set true to configure conda                                                                              |

When specifying images using `source_image_name`, the image must be stored in an [image gallery](https://learn.microsoft.com/en-us/azure/virtual-machines/azure-compute-gallery).
To enable re-using built user resource templates across environments where the image may vary, the image gallery is configured via the `RP_BUNDLE_VALUES` environment variable when deploying the TRE.
The `RP_BUNDLE_VALUES` variable is a JSON object, and the `image_gallery_id` property within it identifies the image gallery that contains the images specified by `source_image_name`:


```bash
RP_BUNDLE_VALUES='{"image_gallery_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/<your-rg>/providers/Microsoft.Compute/galleries/<your-gallery-name>"}
```

