# Guacamole Service bundle

See: [https://guacamole.apache.org/](https://guacamole.apache.org/)

## Firewall Rules

Please be aware that the following Firewall rules are opened for the workspace when this service is deployed:

Service Tags:

- AzureActiveDirectory

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)

## Manual Deployment

!!! caution
    Resources should be deployed using the API (i.e. through the Swagger UI as described in the [setup instructions](../../tre-admins/setup-instructions/installing-workspace-service-and-user-resource.md)). Only deploy manually for development/testing purposes.

1. Create a copy of `templates/workspace_services/guacamole/.env.sample` with the name `.env` and update the variables with the appropriate values.

  | Environment variable name | Description |
  | ------------------------- | ----------- |
  | `ID` | A GUID to identify the workspace service. The last 4 characters of this `ID` can be found in the resource names of the workspace service resources. |
  | `WORKSPACE_ID` | The GUID identifier used when deploying the base workspace bundle. |
  | `GUACAMOLE_IMAGE_TAG` | The tag of the Guacamole Image to use - the tag will be the version (you can find the version in `templates\workspace\services\guacamole\version.txt`) |

1. Build and install the Guacamole Service bundle

  ```cmd
  make porter-build DIR=./templates/workspace_services/guacamole
  make porter-install DIR=./templates/workspace_services/guacamole
  ```
