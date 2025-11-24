# Installing base workspace

## Publishing and registering the base workspace bundle

Run the following in a terminal to build, publish and register the base workpace bundle:

```cmd
make workspace_bundle BUNDLE=base
```

This will prepare the template for use with your TRE.

## Creating a base workspace

Now that we have published and registered a base workspace bundle we can use the deployed API to create a base workspace.

!!! info
    All routes are auth protected. Click the green **Authorize** button to receive a token for Swagger client.

As explained in the [auth guide](../auth.md), every workspace has a corresponding app registration which if you haven't run `make auth`; can be created using the helper script `./devops/scripts/aad/create_workspace_application.sh`. For example:

```bash
  ./devops/scripts/aad/create_workspace_application.sh \
    --name "${TRE_ID} - workspace 1" \
    --admin-consent \
    --ux-clientid "${SWAGGER_UI_CLIENT_ID}" \
    --automation-clientid "${TEST_ACCOUNT_CLIENT_ID}" \
    --application-admin-clientid "${APPLICATION_ADMIN_CLIENT_ID}"
```

!!! caution
    If you're using a separate tenant for Microsoft Entra ID app registrations to the one where you've deployed the TRE infrastructure resources, ensure you've signed into that tenant in the `az cli` before running the above command. See **Using a separate Microsoft Entra ID tenant** in [Setup Auth configuration](setup-auth-entities.md) for more details.

Running the script will report `workspace_api_client_id` and `workspace_api_client_secret` for the generated app. Add these under the authenrication section in `/config.yaml` so that automated testing will work. You also need to use `workspace_api_client_id` in the POST body below.

### Create workspace using the API
Go to `https://<azure_tre_fqdn>/api/docs` and use POST `/api/workspaces` with the sample body to create a base workspace.

```json
{
  "templateName": "tre-workspace-base",
  "properties": {
    "display_name": "manual-from-swagger",
    "description": "workspace for team X",
    "client_id":"<WORKSPACE_API_CLIENT_ID>",
    "client_secret":"<WORKSPACE_API_CLIENT_SECRET>",
    "address_space_size": "medium",
    "workspace_subscription_id": "<OPTIONAL AZURE SUBSCRIPTION ID>"
  }
}
```

The API will return an `operation` object with a `Location` header to query the operation status, as well as the `resourceId` and `resourcePath` properties to query the resource under creation.

You can also follow the progress in Azure portal as various resources come up.

Workspace level operations can now be carried out using the workspace API, at `/api/workspaces/<workspace_id>/docs/`.

### Deploying the workspace to a separate Azure subscription

By specifying an Azure subscription id (a GUID) in the API request or in the UI options the workspace can be created in a separate Azure subscription to the one used for the core TRE resources. The subscription must exist in the same tenant as the core subscription.

There are a few manual steps required to allow the TRE to deploy to a separate subscription. The deployment is done using a managed identity, so this managed identity needs permissions to deploy to the new subscription.

In the core TRE resource group (**_rg-\<treid\>_**) there is a managed identity named **_id-vmss-\<treid\>_**. This is the identity used for deployment and it needs to be granted the [**Owner**][owner] role, or a combination of [**Contributor**][contributor] and [**User Access Administrator**][useradmin] roles at the scope of the new Azure subscription (or management group).

There is also a managed identity named **_id-api-\<treid\>_**. This is the identity the API uses to query the billing API. For the API to be able to report costs for the workspace it will require the [**Billing Reader**][billreader] role on the new Azure subscription (or management group).

## Next steps

* [Installing a workspace service & user resources](./installing-workspace-service-and-user-resource.md)

[owner]: https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/privileged#owner
[contributor]: https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/privileged#contributor
[useradmin]: https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/privileged#user-access-administrator
[billreader]: https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/management-and-governance#billing-reader
