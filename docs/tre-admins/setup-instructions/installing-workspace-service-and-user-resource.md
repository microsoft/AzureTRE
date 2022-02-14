# Installing workspace service and user resource

## Publish and register a workspace service template

We will use the [Guacamole workspace service bundle](./tre-templates/workspace-services/guacamole.md) for the purposes of this tutorial. These steps can be repeated for any workspace service template.

1. Run:

    ```cmd
    make register-bundle DIR=./templates/workspace_services/guacamole BUNDLE_TYPE=workspace_service
    ```

    Copy the resulting JSON payload.

1. Navigate to the Swagger UI at `https://<azure_tre_fqdn>/api/docs`.

1. Log into the Swagger UI by clicking `Authorize`, then `Authorize` again. You will be redirected to the login page.

1. Once logged in. Click `Try it out` on the `POST` `/api/workspace-service-templates` operation.

1. Paste the payload json generated earlier into the `Request body` field, then click `Execute`. Review the server response.

1. To verify registration of the template do `GET` operation on `/api/workspace-service-templates`. The name of the template should now be listed.

## Publish and register a user resource template

The Guacamole workspace service also has user resources, there are the VMs that researchers will deploy. These steps can be repeated for any user resource template.

1. Run:

    ```cmd
    make register-bundle DIR=./templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm BUNDLE_TYPE=user_resource
    ```

    Copy the resulting JSON payload.

1. Navigate to the Swagger UI at `https://<azure_tre_fqdn>/api/docs`. You should already be logged in.

Click `Try it out` on the `POST` `/api/user-resource-templates` operation.

1. In the `service_template_name` field, paste the name of the workspace service template that you registered earlier - `tre-service-guacamole`.

1. Paste the payload json generated earlier into the `Request body` field, then click `Execute`. Review the server response.

1. To verify registration of the template do `GET` operation on `/api/user-resource-templates`. The name of the template should now be listed.

## Creating a workspace service

Now that we have published and registered both workspace service and user resource bundles we can use the workspace API to create a workspace service in our workspace.

1. Navigate to the Swagger UI at `https://<azure_tre_fqdn>/api/workspaces/<workspace_id>/docs` . Where `<workspace_id>` is the workspace ID of the workspace created in the previous step.

!!! info
    All routes are auth protected. Click the green **Authorize** button to receive a token for Swagger client.

1. Log into the Swagger UI by clicking `Authorize`, then `Authorize` again. You will be redirected to the login page.

!!! info
    You need to log in with a user with assigned the WorkspaceOwner role in the app regsitration used when deploying your workspace.

1. Once logged in. Click `Try it out` on the `POST` `/api/workspaces/<workspace_id>/workspace-services` operation.

1. Enter the workspace_id in the `workspace_id` field.

1. Paste the following payload json into the `Request body` field, update `<WORKSPACE_API_CLIENT_ID>` with the client ID of the app registration for the base workspace you created previously, then click `Execute`. Review the server response.

```json
{
  "templateName":"tre-service-guacamole",
  "properties": {
    "display_name":"Virtual Desktop",
    "description":"Create virtual desktops for running research workloads",
    "openid_client_id":"<WORKSPACE_API_CLIENT_ID>",
    "is_exposed_externally":true,
    "guac_disable_copy":true,
    "guac_disable_paste":true
  }
}
```

The API will return an `operation` object with a `Location` header to query the operation status, as well as the `resourceId` and `resourcePath` properties to query the resource under creation. Record this ID for later use.

You can also follow the progress in Azure portal as various resources come up.

!!! info
    There is currently a bug where the redirect URI isn't automatically set up correctly in the Workspace API app registration.
    Until this is fixed, you need to head to the app registration in the Azure portal, click on **Add a redirect URI** > **Add a platform** > **Web** > then paste in the Guacamole URI in the redirect URI box.
    You can find this in the Guacamole app service properties and append `/guacamole/` to the end - it should look like this: `https://guacamole-{TRE_ID}-ws-XXXX-svc-XXXX.azurewebsites.net/guacamole/`). Finally, make sure you check the **ID tokens** checkbox and click **Configure**.

## Creating a user resource

Once the workspace service has been created, we can use the workspace API to create a user resource in our workspace.

1. Navigate to the Swagger UI at `https://<azure_tre_fqdn>/api/workspaces/<workspace_id>/docs` . Where `<workspace_id>` is the workspace ID of your workspace.

1. Click `Try it out` on the `POST` `/api/workspaces/<workspace_id>/workspace-services/<service_id>/user_resources` operation. Where `<workspace_id>` and `<service_id>` are the workspace ID of your workspace and workspace service ID of your workspace service.

1. Enter the workspace ID and workspace service id in the `workspace_id` and `service_id` fields.

1. Paste the following payload json into the `Request body` field, then click `Execute`. Review the server response.

```json
{
  "templateName": "tre-service-guacamole-windowsvm",
  "properties": {
    "display_name": "My VM",
    "description": "Will be using this VM for my research",
    "os_image": "Server 2019 Data Science VM"
  }
}
```

> Note: You can also specify "Windows 10" for a standard Windows 10 image

The API will return an `operation` object with a `Location` header to query the operation status, as well as the `resourceId` and `resourcePath` properties to query the resource under creation.

You can also follow the progress in Azure portal as various resources come up. Once deployment has completed you can connect to the user resource using the `connection_uri` property returned by the API.
