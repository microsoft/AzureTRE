# Installing base workspace

## Publishing and registering the base workspace bundle

1. Run:

    ```cmd
    make register-bundle DIR=./templates/workspaces/base BUNDLE_TYPE=workspace
    ```

    Copy the resulting JSON payload.

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
    ./scripts/aad-app-reg.sh -n 'Workspace One' -r https://mydre.region.cloudapp.azure.com/api/docs/oauth2-redirect -w
```

Running the script will report `WORKSPACE_API_CLIENT_ID` for the generated app which needs to be used in the POST body below.

Go to ``azure_tre_fqdn/docs`` and use POST /api/workspaces with the sample body to create a base workspace.

```json
{
  "templateName": "tre-workspace-base",
  "properties": {
    "display_name": "manual-from-swagger",
    "description": "workspace for team X",
    "app_id": "workspace app id created above"
  }
}
```

The API will report the ``workspace_id`` of the created workspace, which can be used to query deployment status by using ``/api/workspaces/<workspace_id>``. Record the workspace id as you will need it in the next step.

You can also follow the progress in Azure portal as various resources come up.

Workspace level operations can now be carried out using the workspace API, at `/api/workspaces/<workspace_id>/docs/`.

## Next steps

* [Installing a workspace service](./installing-workspace-service-and-user-resource.md)
