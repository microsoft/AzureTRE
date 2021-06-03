# Azure TRE vanilla workspace

## Prerequisites

* [Docker installed](https://docs.docker.com/get-docker/)
* [Porter installed](https://porter.sh/install)
* Azure subscription and a service principal with privileges to provision Azure resources
* TRE core Azure resources deployed, namely:
  * Virtual network
  * Shared subnet
  * Azure Bastion subnet
  * Route table

## Build and run locally

1. Populate environment variables based on the output of the service principal creation script:

    * `AZURE_TENANT_ID`
    * `AZURE_SUBSCRIPTION_ID`
    * `AZURE_CLIENT_ID` - Service principal client ID
    * `AZURE_CLIENT_SECRET` - Service principal client secret (password)

1. Create credentials set named "azure":

    ```plaintext
    porter credentials generate azure
    ```

    * When prompted for the environment variables, enter the name of the environment variable (e.g., `AZURE_TENANT_ID`), not the value! This will generate an `azure.json` file in your Porter home folder.

1. Build the bundle:

    ```plaintext
    porter build --debug
    ```

1. Install the bundle:

    ```plaintext
    porter install --param core_id=mytre-dev-3142 --param workspace_id=0a9e --param location=westeurope --cred azure --debug
    ```

### Custom actions

This Porter bundle implements the following custom actions:

* **show**: Invokes "`terraform show`" to display human-readable output from a state or plan file
* **plan**: Invokes "`terraform plan`" to create an execution plan

To run the custom actions, use `invoke --action` argument, for example:

```plaintext
porter invoke --action plan --param core_id=mytre-dev-3142 --param workspace_id=0a9e --param location=westeurope --cred azure --debug
```

### Clean up

Uninstall the bundle:

```plaintext
porter uninstall --param core_id=mytre-dev-3142 --param workspace_id=0a9e --param location=westeurope --cred azure --debug
```
