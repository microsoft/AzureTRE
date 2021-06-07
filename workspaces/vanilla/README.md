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
* Azure storage account with a container for Terraform backend (for storing the state)

## Build and run locally

### Set environment variables

1. Create a copy of `/workspaces/vanilla/.env.sample` called `/workspaces/vanilla/.env`

1. Update the `.env` file with the workspace parameters and Azure service principal credentials.

### Build and install

**Option 1:** Using the Makefile:

```cmd
make workspaces-vanilla-porter-build
```

```cmd
make workspaces-vanilla-porter-install
```

**Option 2:** Using Porter commands:

1. Load the environment variables into your current session:

    ```cmd
    . ./devops/scripts/load_env.sh ./workspaces/vanilla/.env
    ```

1. Build the bundle:

    ```cmd
    cd ./workspaces/vanilla/
    porter build --debug
    ```

1. Install the bundle:

    ```plaintext
    porter install --parameter-set ./parameters.json --cred ./azure.json --debug
    ```

### Clean up

Uninstall the bundle with Porter uninstall command:

```plaintext
porter uninstall --parameter-set ./parameters.json --cred ./azure.json --debug
```
