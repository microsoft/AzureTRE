# InnerEye Deep Learning and Inference Workspace

This deploys a TRE workspace with the following services:

- [Azure ML](./services/azureml)
- [Azure Dev Test Labs](./services/devtestlabs)
- [InnerEye deep learning](./services/innereye_deeplearning)
- [InnerEye Inference](./services/innereye_inference)

Please follow the above links to learn more about how to access the services and any firewall rules that they will open in the workspace.

## Manual deployment

1. Publish the bundles required for this workspace:

- Vanilla Workspace
    `make porter-build DIR=./workspaces/vanilla`
    `make porter-publish DIR=./workspaces/vanilla`

- Azure ML Service
    `make porter-build DIR=./workspaces/services/azureml`  
    `make porter-publish DIR=./workspaces/services/azureml`

- DevTest Labs Service
    `make porter-build DIR=./workspaces/services/devtestlabs`  
    `make porter-publish DIR=./workspaces/services/devtestlabs`

- InnerEye Deep Learning Service
    `make porter-build DIR=./workspaces/services/innereye_deeplearning`  
    `make porter-publish DIR=./workspaces/services/innereye_deeplearning`

- InnerEye Inference Service
    `make porter-build DIR=./workspaces/services/innereye_inference`  
    `make porter-publish DIR=./workspaces/services/innereye_inference`

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

    `make porter-publish DIR=./workspaces/innereye_deeplearning_inference`
    `make porter-install DIR=./workspaces/innereye_deeplearning_inference`
