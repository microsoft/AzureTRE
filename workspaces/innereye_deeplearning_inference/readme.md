# InnerEye Inference service bundle

See: [https://github.com/microsoft/InnerEye-Inference](https://github.com/microsoft/InnerEye-Inference)

## Deployment

1. Create a service principal with contributor rights over Azure ML:

```cmd
az ad sp create-for-rbac --name <sp-name> --role Contributor --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>/providers/Microsoft.MachineLearningServices/workspaces/<workspace-name>
```

1. Create a copy of `workspaces/innereye_deeplearning_inference/.env.sample` with the name `.env` and update the workspace_id, address_space, and service principal client ID and secret from the previous step.

1. Prerequisites for deployment:

- A deployed TRE instance

- A Vanilla Workspace Bundle published
    `make porter-build DIR=./workspaces/vanilla`
    `make porter-publish DIR=./workspaces/vanilla`

- A Azure ML Service bundle published
    `make porter-build DIR=./workspaces/services/azureml`  
    `make porter-publish DIR=./workspaces/services/azureml`

- A DevTest Labs Service bundle published
    `make porter-build DIR=./workspaces/services/devtestlabs`  
    `make porter-publish DIR=./workspaces/services/devtestlabs`

- A InnerEye Deep Learning Service bundle published
    `make porter-build DIR=./workspaces/services/innereye_deeplearning`  
    `make porter-publish DIR=./workspaces/services/innereye_deeplearning`

- A InnerEye Inference service bundle published
    `make porter-build DIR=./workspaces/services/innereye_inference`  
    `make porter-publish DIR=./workspaces/services/innereye_inference`

1. Publish and install the InnerEye inference workspace:

    `make porter-publish DIR=./workspaces/innereye_deeplearning_inference`
    `make porter-install DIR=./workspaces/innereye_deeplearning_inference`

1. Log onto a VM in the workspace and run:

```cmd
git clone https://github.com/microsoft/InnerEye-Inference
cd InnerEye-Inference
az webapp up --name <inference-app-name> -g <resource-group-name>
```

## Configuring and testing inference service

The workspace service provision an App Service Plan and an App Service for hosting the inference webapp. The webapp will be integrated into the workspace network, allowing the webapp to connect to the AML workspace. Following the setup you will need to:

- Create a new container in your storage account for storing inference images called `inferencedatastore`.
- Create a new folder in that container called `imagedata`.
- Navigate to the ml.azure.com, `Datastores` and create a new datastore named `inferencedatastore` and connect it to the newly created container.
- The key used for authentication is the `inference_auth_key` provided as an output of the service deployment.
- Test the service by sending a GET or POST command using curl or Invoke-WebRequest:
  - Simple ping:
  ```Invoke-WebRequest https://yourservicename.azurewebsites.net/v1/ping -Headers @{'Accept' = 'application/json'; 'API_AUTH_SECRET' = 'your-secret-1234-1123445'}```
  - Test connection with AML:
  ```Invoke-WebRequest https://yourservicename.azurewebsites.net/v1/model/start/HelloWorld:1 -Method POST -Headers @{'Accept' = 'application/json'; 'API_AUTH_SECRET' = 'your-secret-1234-1123445'}```
