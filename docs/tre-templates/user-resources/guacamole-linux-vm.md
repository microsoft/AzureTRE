# Guacamole User Resource Service bundle (Linux)

This is a User Resource Service template. It defines a Linux-based VM to be used by TRE researchers and to be connected to using a [Guacamole server](https://guacamole.apache.org/).
It blocks all inbound and outbound traffic to the internet and allows only RDP connections from within the vnet.

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
- [A guacamole workspace service bundle installed](../workspace-services/guacamole.md)
- [A Nexus shared service has been deployed](../shared-services/nexus.md)

## Notes
- Nexus is a prerequisite of installing the Linux VMs given the additional commands in the bootstrap scripts.
- In production we recommend using VM images to avoid transient issues downloading and installing packages.
- Snap hasn't been configured to work via the nexus proxy

## Using Custom Images
For custom image usage, visit this [page](./custom.md).
