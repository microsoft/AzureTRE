# THIS WILL BE TORN DOWN AND INFO SCATTERED ELSEWHERE

## Details of deployment and infrastructure

The following section is for informational purposes, and the steps don't need to be executed as they are part of make all above.

### Management Infrastructure

We will create management infrastructure in your subscription. This includes resources, such as a storage account and container registry that will enable deployment the Azure TRE. Once the infrastructure is deployed we will build the container images required for deployment. The management infrastructure can serve multiple Azure TRE deployments.

### Bootstrap the back-end state

As a principle, we want all the Azure TRE resources defined in Terraform, including the storage account used by Terraform to hold its back-end state.

A bootstrap script is used to create the initial storage account and resource group using the Azure CLI. Then Terraform is initialized using this storage account as a back-end, and the storage account imported into the state.

You can do this step using the following command but as stated above this is already part of ``make all``.

```cmd
make bootstrap
```

This script should never need running a second time even if the other management resources are modified.

### Management Resource Deployment

The deployment of the rest of the shared management resources is done via Terraform, and the various `.tf` files in the root of this repo.

```cmd
make mgmt-deploy
```

This Terraform creates & configures the following:

- Resource Group (also in bootstrap).
- Storage Account for holding Terraform state (also in bootstrap).
- Azure Container Registry.

### Build and push Docker images

Build and push the docker images required by the Azure TRE and publish them to the container registry created in the previous step.

```bash
make build-api-image
make build-resource-processor-vm-porter-image
make push-api-image
make push-resource-processor-vm-porter-image
```

## Access the Azure TRE deployment

To get the Azure TRE URL, view `azure_tre_fqdn` in the output of the previous `make all` command, or run the following command to see it again:

```cmd
cd templates/core/terraform
terraform output azure_tre_fqdn
```

Open the following URL in a browser, and you should see the Open API docs of Azure TRE API.

```plaintext
https://<azure_tre_fqdn>/docs
```

You can also create a request to the `api/health` endpoint to verify that the API is deployed and responds. You should see a *pong* response as a result of below request.

```cmd
curl https://<azure_tre_fqdn>/api/health
```

## Publishing and registering the base workspace bundle

1. Run:

    ```cmd
    register-bundle DIR=./templates/workspaces/base
    ```

    Copy the resulting payload json.

1. Navigate to the Swagger UI at `https://<azure_tre_fqdn>/docs`

1. Log into the Swagger UI by clicking `Authorize`, then `Authorize` again. You will be redirected to the login page.

1. Once logged in. Click `Try it out` on the `POST` `/api/workspace-templates` operation:

    ![Post Workspace Template](../../assets/post-template.png)

1. Paste the payload json generated earlier into the `Request body` field, then click `Execute`. Review the server response.

1. To verify registration of the template do `GET` operation on `/api/workspace-templates`. The name of the template should now be listed.

## Creating a base workspace

Now that we have published and registered a base workspace bundle we can use the deployed API to create a base workspace.

!!! info
    All routes are auth protected. Click the green **Authorize** button to receive a token for swagger client.  

As explained in the [auth guide](auth.md), every workspace has a corresponding app registration which can be created using the helper script `/scripts/workspace-app-reg.py`. Multiple workspaces can share an app registration.

Running the script will report app id of the generated app which needs to be used in the POST body below.

Go to ``azure_tre_fqdn/docs`` and use POST /api/workspaces with the sample body to create a base workspace.

```json
{
  "displayName": "manual-from-swagger",
  "description": "workspace for team X",
  "workspaceType": "tre-workspace-base",
  "parameters": {},
  "authConfig": {
    "provider": "AAD",
    "data": {
      "app_id": "app id created above"
    }
  }
}
```

The API will report the ``workspace_id`` of the created workspace, which can be used to query deployment status by using ``/api/workspaces/<workspace_id>``

You can also follow the progress in Azure portal as various resources come up.

!!! info
    To query the status using the API your user needs to have TREResearcher or TREOwner role assigned to the app.

## Deleting the Azure TRE deployment

To remove the Azure TRE and its resources from your Azure subscription run:

```cmd
make tre-destroy
```

[letsencrypt]: https://letsencrypt.org/ "A nonprofit Certificate Authority providing TLS certificates to 260 million websites."
