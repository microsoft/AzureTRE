<!-- markdownlint-disable-file MD046 -->
# Upgrading Resources Version

Azure TRE workspaces, workspace services, workspace shared services, and user resources are [Porter](https://porter.sh/) bundles. Porter bundles are based on [Cloud Native Application Bundles (CNAB)](https://cnab.io/).

When a new bundle version becomes available, users can upgrade their resources to a newer version after building, publishing and registering the bundle template.

Upgrades (and downgrades) are based on [CNAB bundle upgrade action](https://getporter.org/bundle/manifest/#bundle-actions).

Bundle template versions follow [semantic versioning rules](../tre-workspace-authors/authoring-workspace-templates.md#versioning).

!!! Note
    Only minor and patch version upgrades are automatically allowed within the Azure TRE upgrade mechanism. Major versions upgrades and any version downgrades are blocked as they are assumed to contain breaking changes or changes that require additional consideration.

    For users who wish to upgrade a major version, we highly recommend to read the changelog, review what has changed and take some appropriate action before upgrading using [force version update](#force-version-update).

## Upgrade existing resources for document-based Porter parameters

Resource Processor 0.13.10 passes parameters through Porter documents. Existing resources can retain command-line parameter overrides from earlier versions. Porter gives these overrides precedence over the current action's parameter set.

Custom actions and uninstall stop with an upgrade-required message when these overrides exist. The Resource Processor also stops these actions if it cannot verify the stored parameters. New installations and resource upgrades clear the overrides through an installation document.

An upgrade runs the bundle's normal upgrade action and can change deployed infrastructure. Plan the usual maintenance window before proceeding.

1. Read the resource's current `templateVersion` and `_etag` using its API `GET` operation.
1. Confirm that the current template version is still registered and its bundle is available.
1. Run the resource's API `PATCH` operation with that same `templateVersion` and the current `_etag`.
1. Wait for the upgrade operation to succeed.
1. Retry the custom action or uninstall.

Follow the [Swagger UI procedure below](#how-to-upgrade-a-resource-using-swagger-ui), using the current template version in the request body. A newer template version is not required.

To remove the firewall rule size limit throughout bundle execution, publish, register and upgrade the firewall shared service to `tre-shared-service-firewall` 1.6.4 or later. Earlier firewall bundles still pass the rules through environment variables.

Upgrade each affected resource separately. Upgrading a workspace does not upgrade its child resources. Before deleting a workspace and its contents, upgrade affected child resources too.

## How to upgrade a resource using Swagger UI

Resources can be upgrade using Swagger UI, in the following example we show how to upgrade a workspace version from 1.0.0 to 1.0.1, other resources upgrades are similar.

1. First make sure the desired template version is registered, [follow these steps if not](../tre-admins/registering-templates.md).

1. Navigate to the Swagger UI at `/api/docs`.

1. Log into the Swagger UI using `Authorize`.

1. Click `Try it out` on the `GET` `/api/workspaces/{workspace_id}` operation.

1. Provide your `workspace_id` in the parameters section and click `Execute`.

1. Copy the `_etag` property from the response body.

1. Click `Try it out` on the `PATCH` `/api/workspaces/{workspace_id}` operation.

1. Provide your `workspace_id` and `_etag` parameters which you've just copied.

1. Provide the following payload with the desired version in the `Request body` parameter and click `Execute`.

    ```json
      {
        "templateVersion": "1.0.1"
      }
    ```
1. Review server response, it should include a new `operation` document with `upgrade` as an `action` and `updating` as `status` for upgrading the workspace and a message states that the Job is starting.

1. Once the upgrade is complete another operation will be created and can be viewed by executing `GET` `/api/workspaces/{workspace_id}/operations`, review it and make sure its `status` is `updated`.

### Force version update
If you wish to upgrade a major version, or downgrade to any version, you can override the blocking in the upgrade mechanism by passing `force_version_update=true` query parameter to the resource `Patch` action.

For example force version patching a workspace:

![Force version update](../assets/swagger_force_version_update.png)
