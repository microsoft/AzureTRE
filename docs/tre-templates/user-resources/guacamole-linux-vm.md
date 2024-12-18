# Guacamole User Resource Service bundle (Linux)

This is a User Resource Service template. It defines a Linux-based VM to be used by TRE researchers and to be connected to using a [Guacamole server](https://guacamole.apache.org/).
It blocks all inbound and outbound traffic to the internet and allows only RDP connections from within the vnet.

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
- [A guacamole workspace service bundle installed](../workspace-services/guacamole.md)
- [A Nexus shared service has been deployed](../shared-services/nexus.md)

## Notes

- Nexus is a prerequisite of installing the Linux VMs given the additional commands in the bootstrap scripts.
- In production we recommend using VM images to avoid transient issues downloading and installing packages. The included user resource templates for VMs with bootstrap scripts should only be used for trial/demonstration purposes. More info can be found [here](./custom.md).
- Snap (app store for linux via [snapcraft.io](https://snapcraft.io)) hasn't been configured to work via the nexus proxy

## Modifying the DPI of the Linux VM display

Depending on the display resolution and your personal preference, you may want to adjust the DPI (Dots Per Inch) setting of your Linux VM to make text and UI elements appear larger or smaller, and hence clearer. This can be done by modifying the Xft.dpi value in `.Xresources` file.

After running this command, you may need to run `reboot` to restart the VM so that the changes to take effect.

## Using Custom Images
For custom image usage, visit this [page](./custom.md).
