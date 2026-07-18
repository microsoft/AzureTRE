# Guacamole User Resource Service bundle (Windows)

This is a User Resource Service template. It defines a Windows 11/Server 2019/Server 2022 VM to be used by TRE researchers and to be connected to using a [Guacamole server](https://guacamole.apache.org/).
It blocks all inbound and outbound traffic to the internet and allows only RDP connections from within the vnet.

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
- [A guacamole workspace service bundle installed](../workspace-services/guacamole.md)
- [A Nexus shared service has been deployed](../shared-services/nexus.md)

## Notes

- Nexus is a prerequisite of installing the Windows VMs given the bootstrap scripts that install data science and Azure tooling.
- In production we recommend using VM images to avoid transient issues downloading and installing packages. The included user resource templates for VMs with bootstrap scripts should only be used for trial/demonstration purposes. More info can be found in the [custom templates documentation](./custom.md).

## Using Custom Images

For custom image usage, visit this [page](./custom.md).
