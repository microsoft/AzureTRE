# InnerEye Deep Learning and Inference Workspace

This deploys a TRE workspace with the following services:

- [Azure ML](../../../templates/workspace_services/azureml)
- [Azure Dev Test Labs](../../../templates/workspace_services/devtestlabs)
- [InnerEye deep learning](../../../templates/workspace_services/innereye_deeplearning)
- [InnerEye Inference](../../../templates/workspace_services/innereye_inference)

Follow the links to learn more about how to access the services and any firewall rules that they will open in the workspace.

## Manual deployment

1. Publish the bundles required for this workspace:

  *Base Workspace*

  ```cmd
  make porter-build DIR=./templates/workspaces/base
  make porter-publish DIR=./templates/workspaces/base
  ```

  *Azure ML Service*

  ```cmd
  make porter-build DIR=./templates/workspace_services/azureml
  make porter-publish DIR=./templates/workspace_services/azureml
  ```

  *DevTest Labs Service*

  ```cmd
  make porter-build DIR=./templates/workspace_services/devtestlabs
  make porter-publish DIR=./templates/workspace_services/devtestlabs
  ```

  *InnerEye Deep Learning Service*

  ```cmd
  make porter-build DIR=./templates/workspace_services/innereye_deeplearning
  make porter-publish DIR=./templates/workspace_services/innereye_deeplearning
  ```

  *InnerEye Inference Service*

  ```cmd
  make porter-build DIR=./templates/workspace_services/innereye_inference
  make porter-publish DIR=./templates/workspace_services/innereye_inference
  ```

1. Create a service principal with contributor rights over Azure ML:

  ```cmd
  az ad sp create-for-rbac --name <sp-name> --role Contributor --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>/providers/Microsoft.MachineLearningServices/workspaces/<workspace-name>
  ```

1. Create a copy of `workspaces/innereye_deeplearning_inference/.env.sample` with the name `.env` and update the variables with the appropriate values.

  | Environment variable name | Description |
  | ------------------------- | ----------- |
  | `WORKSPACE_ID` | A 4 ter unique identifier for the workspace for this TRE. `WORKSPACE_ID` can be found in the resource names of the workspace resources; for example, a `WORKSPACE_ID` of `ab12` will result in a resource group name for workspace of `rg-<tre-id>-ab12`. Allowed characters: Alphanumeric. |
  | `ADDRESS_SPACE` | The address space for the workspace virtual network. For example `192.168.1.0/24`|
  | `INFERENCE_SP_CLIENT_ID` | Service principal client ID used by the inference service to connect to Azure ML. Use the output from the step above. |
  | `INFERENCE_SP_CLIENT_SECRET` | Service principal client secret used by the inference service to connect to Azure ML. Use the output from the step above. |

1. Build and install the workspace:

  ```cmd
  make porter-publish DIR=./templates/workspaces/innereye_deeplearning_inference
  make porter-install DIR=./templates/workspaces/innereye_deeplearning_inference
  ```
