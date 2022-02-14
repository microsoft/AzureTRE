# InnerEye Deep Learning Workspace

This deploys a [Base workspace](./base.md) with the following services inside:

- [Azure ML](../../../templates/workspace_services/azureml)
- [InnerEye](../../../templates/workspace_services/innereye)

Follow the links to learn more about how to access the services and any firewall rules that they will open in the workspace.

## Manual deployment for development and testing

!!! caution
    Resources should be deployed using the API (i.e. through the Swagger UI as described in the [setup instructions](../../tre-admins/setup-instructions/installing-workspace-service-and-user-resource.md)). Only deploy manually for development/testing purposes.

1. Publish the bundles required for this workspace:

  Base Workspace:

  ```cmd
  make porter-build DIR=./templates/workspaces/base
  make porter-publish DIR=./templates/workspaces/base
  ```

  Azure ML Service:

  ```cmd
  make porter-build DIR=./templates/workspace_services/azureml
  make porter-publish DIR=./templates/workspace_services/azureml
  ```

1. Create a copy of `workspaces/innereye/.env.sample` with the name `.env` and update the variables with the appropriate values.

  | Environment variable name | Description |
  | ------------------------- | ----------- |
  | `ID` | A GUID to identify the workspace. The last 4 characters of this `ID` can be found in the resource names of the workspace resources; for example, a `ID` of `2e84dad0-9d4f-42bd-8e44-3d04095eab12` will result in a resource group name for workspace of `rg-<tre-id>-ab12`. |
  | `ADDRESS_SPACE` | The address space for the workspace virtual network, must be inside the `TRE_ADDRESS_SPACE` defined when deploying the TRE and not overlap with any other address spaces. |
  | `INFERENCE_SP_CLIENT_ID` | Service principal client ID used by the inference service to connect to Azure ML. Use the output from the step above. |
  | `INFERENCE_SP_CLIENT_SECRET` | Service principal client secret used by the inference service to connect to Azure ML. Use the output from the step above. |

1. Build and install the workspace:

  ```cmd
  make porter-build DIR=./templates/workspaces/innereye
  make porter-install DIR=./templates/workspaces/innereye
  ```
