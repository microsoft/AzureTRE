# Registering Templates

To enable users to deploy Workspaces, Workspace Services or User Resources, we need to register their Templates. This can be done wither by running `make` commands; using the API or devops scripts. In this article both approaches are described.

!!! info
    Templates are encapsulated in [Porter](https://porter.sh) bundles.

## Registration with make commands

Porter bundles can be registered with `make` commands which can be useful for CI/CD scenarios. To start on should build the Porter bundle running the command `make bundle-build`. Once built a Template must be published so it can the registered. For this the commands `make bundle publish` and `make bundle-register` can be used Here we use the workspace service Azure ML bundle as an example:

```cmd
make bundle-build DIR=templates/workspace_services/azureml
make bundle-publish DIR=templates/workspace_services/azureml
make bundle-register DIR=templates/workspace_services/azureml BUNDLE_TYPE=workspace_service
```

## Registration using Swagger UI

Porter bundles can also be registered interactively using the Swagger UI. For that we need to build and publish the porter bundle  

1. Build the Porter bundle

   ```cmd
   make bundle-build DIR=templates/workspace_services/azureml
   make bundle-publish DIR=templates/workspace_services/azureml
   ```

1. Use the utility script to generate the payload. The script needs to be executed from within the bundle directory, for example `/templates/workspaces/base/`

   ```cmd
   ../../../devops/scripts/register_bundle_with_api.sh -r <acr_name> -i -t workspace
   ```

   Copy the resulting JSON payload.

1. Navigate to the Swagger UI at `/api/docs`
1. Log into the Swagger UI using `Authorize`
1. Click `Try it out` on the `POST` `/api/workspace-templates` operation:

    ![Post Workspace Template](../assets/post-template.png)

1. Paste the payload json generated earlier into the `Request body` field, then click `Execute`. Review the server response.
1. Verify the template registration using the `GET` operation on `/api/workspace-templates`. The name of the template should now be listed.

## Registration using script

To use the script to automatically register the template, you must create a user that does not require an interactive login per the [e2e test user documentation here](../tre-admins/auth.md#tre-e2e-test).

The script needs to be executed from within the bundle directory, for example `/templates/workspaces/base/`

```cmd
Usage: ../../../devops/scripts/register_bundle_with_api.sh [-u --tre_url]  [-c --current] [-i --insecure]

Options:
   -r, --acr-name                Azure Container Registry Name
   -t, --bundle-type             Bundle type: workspace, workspace_service, user_resource or shared_service
   -w, --workspace-service-name  The template name of the user resource (if registering a user_resource)
   -c, --current                 Make this the currently deployed version of this template
   -i, --insecure                Bypass SSL certificate checks
   -u, --tre_url                 URL for the TRE (required for automatic registration)
   -a, --access-token            Azure access token to automatically post to the API (required for automatic registration)
   -v, --verify                  Verify registration with the API
```

In addition to generating the payload, the script posts the payload to the `/api/workspace-templates` endpoint. Once registered the template can be retrieved by a `GET` operation on `/api/workspace-templates`.

!!! tip
    Follow the same procedure to register workspace service templates and user resource templates
