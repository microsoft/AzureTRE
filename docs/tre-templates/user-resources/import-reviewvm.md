# Guacamole User Resource Service bundle (Windows)

This is a User Resource Service template. It defines a VM to be used by TRE Airlock Managers with [Guacamole server](https://guacamole.apache.org/).
It blocks all inbound traffic to the internet and allows only RDP connections from within the vnet.

When deployed in an Airlock Import Review workspace, it has access to the Airlock Import In-Progress storage account outside of the workspace. For more information about Airlock, see [overview page](../../azure-tre-overview/airlock.md).

Data that needs to be reviewed will be downloaded onto the VM during VM creation, and available on Desktop.

It can be only deployed by an Airlock Manager.

## Prerequisites

- [An Airlock Import workspace bundle installed](../workspaces/airlock-import-review.md)
- [A guacamole workspace service bundle installed in that workspace](../workspace-services/guacamole.md)
