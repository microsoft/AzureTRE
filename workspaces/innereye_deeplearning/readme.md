# InnerEye Deep Learning Workspace

This deploys a TRE workspace with the following services:

- [Azure ML](./services/azureml)
- [Azure Dev Test Labs](./services/devtestlabs)
- [InnerEye deep learning](./services/innereye_deeplearning)

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

1. Create a copy of `workspaces/innereye_deeplearning/.env.sample` with the name `.env` and update the variables with the appropriate values.

1. Build and install the workspace:

    `make porter-publish DIR=./workspaces/innereye_deeplearning`
    `make porter-install DIR=./workspaces/innereye_deeplearning`
