# InnerEye Inference service bundle

See: [https://github.com/microsoft/InnerEye-Inference](https://github.com/microsoft/InnerEye-Inference)

## Manual Deployment

1. Prerequisites for deployment:
    - [A workspace with an InnerEye Deep Learning bundle installed](../innereye_deep_learning)

1. Create a service principal with contributor rights over the subscription. This will be replaced with a Managed Identity in the future:

```cmd
az ad sp create-for-rbac --name <sp-name> --role Contributor --scopes /subscriptions/<subscription-id>
```

1. Create a copy of `workspaces/services/innereye_inference/.env.sample` with the name `.env` and update the variables with the appropriate values.

| Environment variable name | Description |
| ------------------------- | ----------- |
| `WORKSPACE_ID` | The 4 character unique identifier used when deploying the vanilla workspace bundle. |
| `AZUREML_WORKSPACE_NAME` | Name of the Azure ML workspace deployed as part of the Azure ML workspace service prerequisite. |
| `AZUREML_ACR_ID` | ID of the Azure Container Registry deployed as part of the Azure ML workspace service prerequisite. |
| `INFERENCE_SP_CLIENT_ID` | Service principal client ID used by the inference service to connect to Azure ML. Use the output from the step above. |
| `INFERENCE_SP_CLIENT_SECRET` | Service principal client secret used by the inference service to connect to Azure ML. Use the output from the step above. |

1. Build and deploy the InnerEye Inference service
    - `make porter-build DIR=./workspaces/services/innereye_inference`  
    - `make porter-install DIR=./workspaces/services/innereye_inference`

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
