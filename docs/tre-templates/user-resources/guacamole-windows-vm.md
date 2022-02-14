# Guacamole User Resource Service bundle (Windows)

This is a User Resource Service template. It defines a Windows 10/Server 2019 VM to be used by TRE researchers and to be connected to using a [Guacamole server](https://guacamole.apache.org/).
It blocks all inbound and outbound traffic to the internet and allows only RDP connections from within the vnet.

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
- [A guacamole workspace service bundle installed](../workspace-services/guacamole.md)

## Manual Deployment

!!! caution
    Resources should be deployed using the API (i.e. through the Swagger UI as described in the [setup instructions](../../tre-admins/setup-instructions/installing-workspace-service-and-user-resource.md)). Only deploy manually for development/testing purposes.

1. Create a copy of `templates/workspace_services/guacamole/.env.sample` with the name `.env` and update the variables with the appropriate values.

  | Environment variable name | Description |
  | ------------------------- | ----------- |
  | `ID` | A GUID to identify the workspace service. The last 4 characters of this `ID` can be found in the resource names of the workspace service resources. |
  | `WORKSPACE_ID` | The GUID identifier used when deploying the base workspace bundle. |
  | `PARENT_SERVICE_ID` | The unique identifier of this service parent (a Guacamole service) |
  | `OS_IMAGE` | Name of the OS image to use for the VM (i.e. `Windows 10` or `Server 2019 Data Science VM`) |

1. Build and install the Guacamole Service bundle

  ```cmd
  make porter-build DIR=./templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm
  make porter-install DIR=./templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm
  ```
