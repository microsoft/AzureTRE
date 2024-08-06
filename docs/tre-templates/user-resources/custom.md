# Guacamole User Resources

- linuxvm - a Linux-based virtual machine
- windowsvm - A Windows-based virtual machine

## Customising the user resources

The `guacamole-azure-linuxvm` and `guacamole-azure-windowsvm` folders follow a consistent layout.
To update one of these templates (or to create a new template based on these folders) to use different image details or VM sizes, there are a few files that need to be updated:

| File                   | Description                                                                                                                                                                                                                                                                        |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `porter.yaml`          | This file describes the template and the name should be updated when creating a template based on the folder.<br> This file also contains a `custom` data section that describes the VM properties.<br> Additionally, the version needs to be updated to deploy an updated version |
| `template_schema.json` | This file controls the validation applied to the template, for example specifying the valid options for fields such as size and image                                                                                                                                              |

### Configuration

In `porter.yaml`, the `custom` section contains a couple of sub-sections (shown below)

```yaml
custom:
  vm_sizes:
    "2 CPU | 8GB RAM": Standard_D2s_v5
    "4 CPU | 16GB RAM": Standard_D4s_v5
    "8 CPU | 32GB RAM": Standard_D8s_v5
    "16 CPU | 64GB RAM": Standard_D16s_v5
  image_options:
    "Ubuntu 22.04 LTS":
      source_image_reference:
        publisher: canonical
        offer: 0001-com-ubuntu-server-jammy
        sku: 22_04-lts-gen2
        version: latest
        apt_sku: 22.04
      install_ui: true
      conda_config: false
    # "Custom Image From Gallery":
    #   source_image_name: your-image
    #   install_ui: true
    #   conda_config: true
```

The `vm_sizes` section is a map of a custom SKU description to the SKU identifier.

The `image_options` section defined the possible image choices for the template (note that the name of the image used here needs to be included in the corresponding enum in `template_schema.json`).

Within the image definition in `image_options` there are a few properties that can be specified:

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
