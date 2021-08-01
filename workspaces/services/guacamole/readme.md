# Guacamole Service bundle

See: [https://guacamole.apache.org/](https://guacamole.apache.org/)

## Firewall Rules

Please be aware that the following Firewall rules are opened for the workspace when this service is deployed:

URLs:

TBD

## Manual Deployment

1. Prerequisites for deployment:
    - [A vanilla workspace bundle installed](../../vanilla)

1. Create a copy of `workspaces/services/guacamole/.env.sample` with the name `.env` and update the variables with the appropriate values.

| Environment variable name | Description |
| ------------------------- | ----------- |
| `WORKSPACE_ID` | The 4 character unique identifier used when deploying the vanilla workspace bundle. |
| `GUACAMOLE_IMAGE_TAG` | Image tag of the Guacamole server |

1. Build and install the Guacamole Service bundle
    - `make porter-build DIR=./workspaces/services/guacamole`  
    - `make porter-install DIR=./workspaces/services/guacamole`
