# Azure Virtual Desktop User Resources

This folder contains user resources that can be deployed with the Azure Virtual Desktop workspace service:

- `avd-personal-sessionhost` - A Windows-based personal session host VM that joins the AVD host pool

## Customising the user resources

The `avd-personal-sessionhost` folder follows a consistent layout.
To update this template (or to create a new template based on this folder) to use different image details or VM sizes, there are a few files that need to be updated:

| File                   | Description                                                                                                                                                                                                                                                                        |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `porter.yaml`          | This file describes the template and the name should be updated when creating a template based on the folder.<br> This file also contains a `custom` data section that describes the VM properties.<br> Additionally, the version needs to be updated to deploy an updated version |
| `template_schema.json` | This file controls the validation applied to the template, for example specifying the valid options for fields such as size and image                                                                                                                                              |

### Configuration

In `porter.yaml`, the `custom` section contains a couple of sub-sections (shown below)

```yaml
custom:
  vm_sizes:
    "2 CPU | 8GB RAM": Standard_D2s_v6
    "4 CPU | 16GB RAM": Standard_D4s_v6
    "8 CPU | 32GB RAM": Standard_D8s_v6
    "16 CPU | 64GB RAM": Standard_D16s_v6
  image_options:
    "Windows 11 Multi-Session":
      source_image_reference:
        publisher: microsoftwindowsdesktop
        offer: windows-11
        sku: win11-24h2-avd
        version: latest
      secure_boot_enabled: true
      vtpm_enabled: true
```

The `vm_sizes` section is a map of a custom SKU description to the SKU identifier.

The `image_options` section defines the possible image choices for the template (note that the name of the image used here needs to be included in the corresponding enum in `template_schema.json`).

Within the image definition in `image_options` there are a few properties that can be specified:

| Name                     | Description                                                                                              |
| ------------------------ | -------------------------------------------------------------------------------------------------------- |
| `source_image_reference` | Specify VM image to use by `publisher`, `offer`, `sku` & `version` (e.g. for Azure Marketplace images)   |
| `secure_boot_enabled`    | Set true to enable [Secure Boot](https://learn.microsoft.com/en-us/azure/virtual-machines/trusted-launch#secure-boot). Requires a [Gen 2](https://learn.microsoft.com/en-us/azure/virtual-machines/generation-2) VM image |
| `vtpm_enabled`           | Set true to enable [vTPM](https://learn.microsoft.com/en-us/azure/virtual-machines/trusted-launch#vtpm). Requires a [Gen 2](https://learn.microsoft.com/en-us/azure/virtual-machines/generation-2) VM image |

## Connecting to AVD

Users can access their personal session hosts through:

1. **Windows App web client**: [https://windows.cloud.microsoft](https://windows.cloud.microsoft)
2. **Windows Desktop Client**: Download from [Microsoft Store](https://aka.ms/wvd/clients/windows)
3. **macOS Client**: Download from [Mac App Store](https://aka.ms/wvd/clients/mac)

The session host automatically joins the AVD host pool and uses Microsoft Entra ID for authentication, supporting external identities.
Users can own multiple personal desktops in the same host pool. Each resource's Connect action opens that VM directly using its AVD session-host object ID. Windows App shows the resource's display name under the TRE workspace heading; use distinct names for multiple desktops. Names are applied during install or upgrade. Owners must also belong to an entitled workspace group to see their desktops.
