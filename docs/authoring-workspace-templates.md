# Authoring workspaces templates

<!-- markdownlint-disable-next-line MD013 -->
Azure TRE workspaces are [Porter](https://porter.sh/) bundles that in turn are based on [Cloud Native Application Bundles (CNAB)](https://cnab.io/). Workspace authors are free to choose the technology stack for provisioning resources (e.g., ARM templates, Terraform etc.), but the Azure TRE framework sets certain requirements for the bundle manifests, which specify the credentials, input and output parameters, deployment actions among other things. The document describes those requirements.

**Use [the vanilla workspace bundle](../workspaces/vanilla/README.md) and [others](../workspaces/) as reference** or as the basis for the new bundle. To start from scratch follow the Porter [Quickstart Guide](https://porter.sh/quickstart/) ([`porter create` CLI command](https://porter.sh/cli/porter_create/) will generate a new bundle in the current directory).

## Prerequisites

* [Docker installed](https://docs.docker.com/get-docker/)
* [Porter installed](https://porter.sh/install)
* Azure TRE instance deployed to test against

## Workspace bundle manifest

The manifest of a workspace bundle is the `porter.yaml` file (see [Author Bundles in Porter documentation](https://porter.sh/author-bundles/)). This section describes the mandatory credentials, input and output parameters of a TRE workspace bundle.

### Credentials

A workspace bundle requires the following [credentials](https://porter.sh/author-bundles/#credentials) to provision resources in Azure:

* [Azure tenant ID](https://docs.microsoft.com/en-us/azure/active-directory/fundamentals/active-directory-how-to-find-tenant)
* Azure subscription ID
* The client ID of a [service principal](https://docs.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals) with privileges to provision resources
* The client secret (password) of a service principal

The credentials are provided as environment variables by the deployment runner. The bundle author must use the following environment variable names:

* `ARM_TENANT_ID`
* `ARM_SUBSCRIPTION_ID`
* `ARM_CLIENT_ID`
* `ARM_CLIENT_SECRET`

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

| Parameter | Type | Description | Example value |
| --------- | ---- | ----------- | ------------- |
| `tre_id` | string | Unique ID of for the TRE instance. | `tre-dev-42` |
| `workspace_id` | string | Unique 4-character long, alphanumeric workspace ID. | `0a9e` |
| `azure_location` | string | Azure location (region) to deploy the workspace resource to. | `westeurope` |
| `address_space` | string | VNet address space for the workspace services. | `10.2.1.0/24` |

`tre_id` can be found in the resource names of the Azure TRE instance; for example the resource group name of the Azure TRE instance based on the example in the above table would be "`rg-tre-dev-42`".

Similarly to `tre_id`, `workspace_id` is used in the resource names of the workspace. The resource group name of the workspace must be of form "`rg-<tre_id>-ws-<workspace_id>`", for example: "`rg-tre-dev-42-ws-0a9e`".

All the values for the required parameters will be provided by the deployment runner.

Any **custom parameters** are picked up by Azure TRE Management API and will be queried from the user deploying the workspace bundle so make sure to write clear descriptions of the parameters as these are shown in the user interface to guide the user.

### Output

> **TBD:** After a workspace with virtual machines is implemented this section can be written based on that. ([Outputs in Porter documentation](https://porter.sh/author-bundles/#outputs) to be linked here too.)

### Actions

The required actions are the main two of CNAB spec:

* `install` - Deploys/repairs the workspace Azure resources, and must be **idempotent**
* `uninstall` - Tears down (deletes) the Azure resources of the workspace and its services

## Supported Porter mixins

The deployment runner of Azure TRE supports the following [Porter mixins](https://porter.sh/mixins/):

* [exec](https://porter.sh/mixins/exec/)
* [az](https://github.com/getporter/az-mixin)
* [arm](https://porter.sh/mixins/arm/)
* [terraform](https://github.com/getporter/terraform-mixin)

To add support for additional mixins including custom ones, [the Porter installation script of TRE](../devops/scripts/install_porter.sh) needs to be modified.

## Versioning

Workspace versions are the bundle versions specified in [the metadata](https://porter.sh/author-bundles/#bundle-metadata). The bundle versions should match the image tags in the container registry (see [Publishing workspace bundle](#publishing-workspace-bundle)).

TRE does not provide means to update an existing workspace to a newer version. Instead, the user has to first uninstall the old version and then install the new one. The CNAB **upgrade** or a Porter custom ("`update`") action may be used in the future version of TRE to do this automatically.

## Publishing workspace bundle

See [Registering workspace templates](./registering-workspace-templates.md).
