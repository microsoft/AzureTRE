# Authoring templates

Azure TRE workspaces, workspace services, shared services, and user resources are [Porter](https://porter.sh/) bundles. Porter bundles are based on [Cloud Native Application Bundles (CNAB)](https://cnab.io/).

Authors are free to choose the technology stack for provisioning resources (e.g., ARM templates, Terraform etc.), but the Azure TRE framework sets certain requirements for the bundle manifests, which specify the credentials, input and output parameters, deployment actions among other things.

This document describes the requirements, and the process to author a template.

!!! tip
    Use [the base workspace bundle](../tre-templates/workspaces/base.md) as reference or as the basis for the new bundle.

To create a bundle from scratch follow the Porter [Quickstart Guide](https://porter.sh/quickstart/) ([`porter create` CLI command](https://porter.sh/cli/porter_create/) will generate a new bundle in the current directory).

Read more about Porter in [Resource Processor doc](../tre-developers/resource-processor.md#porter).

## Prerequisites

* [Docker installed](https://docs.docker.com/get-docker/)
* [Porter installed](https://porter.sh/install)
* Azure TRE instance deployed to test against

## Workspace bundle manifest

The manifest of a workspace bundle is the `porter.yaml` file (see [Author Bundles in Porter documentation](https://porter.sh/author-bundles/)). This section describes the mandatory credentials, input and output parameters of a TRE workspace bundle.

### Credentials

A workspace bundle requires the following [credentials](https://porter.sh/author-bundles/#credentials) to provision resources in Azure:

* [Azure tenant ID](https://learn.microsoft.com/en-us/entra/fundamentals/how-to-find-tenant)
* Azure subscription ID
* The client ID of a [service principal](https://learn.microsoft.com/en-us/entra/identity-platform/app-objects-and-service-principals?tabs=browser) with privileges to provision resources
* The client secret (password) of a service principal

The credentials are provided as environment variables by the deployment runner. The bundle author must use the following environment variable names:

```bash
ARM_TENANT_ID
ARM_SUBSCRIPTION_ID
ARM_CLIENT_ID
ARM_CLIENT_SECRET
```

The names of the Porter credentials (`name` field in `porter.yaml`) can be freely chosen by the author.

Example:

```yaml
credentials:
  - name: azure_tenant_id
    env: ARM_TENANT_ID
  - name: azure_subscription_id
    env: ARM_SUBSCRIPTION_ID
  - name: azure_client_id
    env: ARM_CLIENT_ID
  - name: azure_client_secret
    env: ARM_CLIENT_SECRET
```

### Parameters

This section describes the mandatory [(input) parameters](https://porter.sh/author-bundles/#parameters) of a workspace bundle manifest.

| <div style="width:120px">Parameter</div> | Type | Description | Example value |
| --------- | ---- | ----------- | ------------- |
| `tre_id` | string | Unique ID of for the TRE instance. | `tre-dev-42` |
| `workspace_id` | string | Unique 4-character long, alphanumeric workspace ID. | `0a9e` |
| `azure_location` | string | Azure location (region) to deploy the workspace resource to. | `westeurope` |
| `address_space` | string | VNet address space for the workspace services. | `10.2.1.0/24` |

`tre_id` can be found in the resource names of the Azure TRE instance; for example the resource group name of the Azure TRE instance based on the example in the above table would be "`rg-tre-dev-42`".

Similarly to `tre_id`, `workspace_id` is used in the resource names of the workspace. The resource group name of the workspace must be of form "`rg-<tre_id>-ws-<workspace_id>`", for example: "`rg-tre-dev-42-ws-0a9e`".

All the values for the required parameters will be provided by the deployment runner.

Any **custom parameters** are picked up by Azure TRE API and will be queried from the user deploying the workspace bundle. Custom parameters should also be defined in the `template_schema.json` file at the root of the bundle. This file follows the [JSON schema standard](http://json-schema.org/) and can be used by a user interface to generate a UI for the user to input the parameters.

### Output

!!! todo
    After a workspace with virtual machines is implemented this section can be written based on that. ([Outputs in Porter documentation](https://porter.sh/author-bundles/#outputs) to be linked here too.)

### Actions

The required actions are the main two of CNAB spec:

* `install` - Deploys/repairs the workspace Azure resources, and must be **idempotent**
* `uninstall` - Tears down (deletes) the Azure resources of the workspace and its services

## Workspace service bundle manifests

Workspace service bundles are generated in the same way as workspace bundles.

The mandatory parameters for workspace services are:

| Parameter | Type | Description | Example value |
| --------- | ---- | ----------- | ------------- |
| `tre_id` | string | Unique ID of for the TRE instance. | `tre-dev-42` |
| `workspace_id` | string | Unique 4-character long, alphanumeric workspace ID. | `0a9e` |

### Workpace services requiring additional address sapces

Some workspace services may require additional address spaces to be provisioned. This may be as they need advanced network security groups, route tables or delegated subnets.

To request an additional address space, the workspace service bundle must define an `address_space` parameter in the `porter.yaml` file. The value of this parameter will be provided by API to the resource processor.

The size of the `address_space` will default to `/24`, however other sizes can be requested by including an `address_space_size` as part of the workspace service template.

## User resource bundle manifests

User Resource bundles are generated in the same way as workspace bundles and workspace services bundles.
The main difference is that a workspace service type needs to be supplied when registering a user resource template, as it only applies to a given workspace service.

The mandatory parameters for User Resources are:

| Parameter | Type | Description | Example value |
| --------- | ---- | ----------- | ------------- |
| `tre_id` | string | Unique ID of for the TRE instance. | `tre-dev-42` |
| `workspace_id` | string | Unique 4-character long, alphanumeric workspace ID. | `0a9e` |

## Azure Resources Tagging

TRE Cost Reporting is based on Azure tagging to be able to generate cost report for core services, shared services, workspace, workspace services and user resources.
Templates authors need to make sure that underling Azure resources are tagged with the relevent tags, for more information see [cost reporting](../azure-tre-overview/cost-reporting.md#azure-resources-tagging):

## Versioning

Workspace versions are the bundle versions specified in [the metadata](https://porter.sh/author-bundles/#bundle-metadata). The bundle versions should match the image tags in the container registry (see [Publishing workspace bundle](#publishing-workspace-bundle)).

Bundle versions should follow [Semantic Versioning](https://semver.org/), given a version number **MAJOR.MINOR.PATCH**, increment the:

1. **MAJOR** version when you make a breaking change, potential data loss, changes that don't easily/automatically upgrade, or significant changes which require someone to review what has changed and take some appropriate action, or functionality of the component has significantly changed and users might need training.

2. **MINOR** version when you add minor functionality which can be automatically upgraded.

3. **PATCH** version when you make backward-compatible bug or typo fixes.


For resource version upgrades see [Upgrading Resources Version](../tre-admins/upgrading-resources.md).

## Publishing workspace bundle

See [Registering workspace templates](../tre-admins/registering-templates.md).

## Manual Deployment

!!! caution
    Resources should be deployed using the API (i.e. through the Swagger UI as described in the [setup instructions](../tre-admins/setup-instructions/installing-base-workspace.md)). Only deploy manually for development/testing purposes.

1. Create a copy of the Porter bundle's environment settings from `/templates/<scope>/.env.sample` with the name `.env` and update the variables with the appropriate values.

1. Build and deploy the Porter bundle

  ```cmd
  make bundle-build DIR=./templates/<scope>/<bundle_name>
  make bundle-publish DIR=./templates/<scope>/<bundle_name> 
  make bundle-register DIR=./templates/<scope>/<bundle_name> BUNDLE_TYPE=<scope>
  ```
