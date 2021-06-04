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

1. Create a copy of `.env.sample` called `.env`

1. Update the `.env` with the workspace parameters and azure service principal credentials.

### Either install using the makefile

3. Run `make workspaces-vanilla-porter-build`

4. Run `make workspaces-vanilla-porter-install`

### Or install using porter

3. Load the environment variables into your current session:

    ```cmd
    . ./devops/scripts/load_env.sh ./workspaces/vanilla/.env 
    ```

4. Build the bundle:

    ```cmd
    cd ./workspaces/vanilla/
    porter build --debug
    ```

5. Install the bundle:

    ```plaintext
    porter install -p ./parameters.json --cred ./azure.json --debug
    ```

### Custom actions

This Porter bundle implements the following custom actions:

* **show**: Invokes "`terraform show`" to display human-readable output from a state or plan file
* **plan**: Invokes "`terraform plan`" to create an execution plan

To run the custom actions, use `invoke --action` argument, for example:

```plaintext
porter invoke --action plan -p ./parameters.json --cred ./azure.json --debug
```

### Clean up

Uninstall the bundle:

```plaintext
porter uninstall --param tre_id=mytre-dev-3142 --param workspace_id=0a9e --param location=westeurope --cred azure --debug
```
