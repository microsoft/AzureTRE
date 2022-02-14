# Installing base workspace

## Publishing and registering the base workspace bundle

1. Run:

    ```cmd
    make register-bundle DIR=./templates/workspaces/base BUNDLE_TYPE=workspace
    ```

    Copy the resulting JSON payload.

!!! info
    If you're using Codespaces, you may encounter a `Permission denied` issue with the Docker daemon. To fix this, run `sudo bash ./devops/scripts/set_docker_sock_permission.sh` from the root of the repository, then retry the make command.

1. Navigate to the Swagger UI at `https://<azure_tre_fqdn>/api/docs`

1. Log into the Swagger UI by clicking `Authorize`, then `Authorize` again. You will be redirected to the login page.

1. Once logged in. Click `Try it out` on the `POST` `/api/workspace-templates` operation:

    ![Post Workspace Template](../../assets/post-template.png)

1. Paste the payload json generated earlier into the `Request body` field, then click `Execute`. Review the server response.

1. To verify registration of the template do `GET` operation on `/api/workspace-templates`. The name of the template should now be listed.

## Creating a base workspace

Now that we have published and registered a base workspace bundle we can use the deployed API to create a base workspace.

!!! info
    All routes are auth protected. Click the green **Authorize** button to receive a token for Swagger client.

As explained in the [auth guide](../auth.md), every workspace has a corresponding app registration which can be created using the helper script `scripts/aad-app-reg.sh`. For example:

```bash
    ./scripts/aad-app-reg.sh --name 'Workspace One' --swaggerui-redirecturl https://mytre.region.cloudapp.azure.com/api/docs/oauth2-redirect --workspace
```

!!! caution
    If you're using a separate tenant for AAD app registrations to the one where you've deployed the TRE infrastructure resources, ensure you've signed into that tenant in the `az cli` before running the above command. See **Using a separate Azure Active Directory tenant** in [Pre-deployment steps](./pre-deployment-steps.md) for more details.

Running the script will report `WORKSPACE_API_CLIENT_ID` for the generated app which needs to be used in the POST body below.

Go to `https://<azure_tre_fqdn>/api/docs` and use POST `/api/workspaces` with the sample body to create a base workspace.

```json
{
  "templateName": "tre-workspace-base",
  "properties": {
    "display_name": "manual-from-swagger",
    "description": "workspace for team X",
    "app_id": "WORKSPACE_API_CLIENT_ID",
    "address_space_size": "medium"
  }
}
```

The API will return an `operation` object with a `Location` header to query the operation status, as well as the `resourceId` and `resourcePath` properties to query the resource under creation.

You can also follow the progress in Azure portal as various resources come up.

Workspace level operations can now be carried out using the workspace API, at `/api/workspaces/<workspace_id>/docs/`.

## Next steps

* [Installing a workspace service](./installing-workspace-service-and-user-resource.md)
