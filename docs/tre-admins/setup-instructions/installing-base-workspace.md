# Installing base workspace

## Publishing and registering the base workspace bundle

1. Run:

    ```cmd
    /workspaces/tre> make register-bundle DIR=./templates/workspaces/base BUNDLE_TYPE=workspace
    ```

    Copy the resulting JSON payload.

1. Navigate to the Swagger UI at `https://<azure_tre_fqdn>/docs`

1. Log into the Swagger UI by clicking `Authorize`, then `Authorize` again. You will be redirected to the login page.

1. Once logged in. Click `Try it out` on the `POST` `/api/workspace-templates` operation:

    ![Post Workspace Template](../../assets/post-template.png)

1. Paste the payload json generated earlier into the `Request body` field, then click `Execute`. Review the server response.

1. To verify registration of the template do `GET` operation on `/api/workspace-templates`. The name of the template should now be listed.

## Creating a base workspace

Now that we have published and registered a base workspace bundle we can use the deployed API to create a base workspace.

!!! info
    All routes are auth protected. Click the green **Authorize** button to receive a token for Swagger client.

As explained in the [auth guide](../auth.md), every workspace has a corresponding app registration which can be created using the helper script `/scripts/workspace-app-reg.py`. Multiple workspaces can share an app registration.

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
    To query the status using the API your user needs to have `TREResearcher` or `TREOwner` role assigned to the app.
