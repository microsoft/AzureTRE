# Guacamole Service bundle

See: [https://guacamole.apache.org/](https://guacamole.apache.org/)

## Firewall Rules

Please be aware that the following Firewall rules are opened for the workspace when this service is deployed:

URLs:

!!! todo
    Add firewall rules

## Prerequisites

- [A base workspace bundle installed](../../../templates/workspaces/base)

## Manual Deployment


1. Create a copy of `templates/workspace_services/guacamole/.env.sample` with the name `.env` and update the variables with the appropriate values.

  | Environment variable name | Description |
  | ------------------------- | ----------- |
  | `WORKSPACE_ID` | The 4 character unique identifier used when deploying the base workspace bundle. |
  | `GUACAMOLE_IMAGE_TAG` | Image tag of the Guacamole server |

1. Build and install the Guacamole Service bundle

  ```cmd
  make porter-build DIR=./templates/workspace_services/guacamole
  make porter-install DIR=./templates/workspace_services/guacamole
  ```
