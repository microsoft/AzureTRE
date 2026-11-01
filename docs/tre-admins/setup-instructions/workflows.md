# GitHub Actions workflows (CI/CD)

To deploy the Azure TRE using GitHub workflows, create a fork of the repository.

Deployment is done using the `/.github/workflows/deploy_tre.yml` workflow. This method is also used to deploy the dev/test environment for the original Azure TRE repository.

## Isolated CI environments

PR comment tests and branch validation derive their environment names from the Git reference, Azure cloud and deployment location.
Repeated runs in the same cloud and location reuse the environment. Changing the location creates a separate environment, including its management account and Key Vault names.
This prevents a retained, purge-protected vault in the previous location from blocking deployment in the new location.
Terraform continues to recover soft-deleted vaults in the same location through its existing provider configuration.

The first run after adopting these names must include deployment. Use `/test COMMIT_SHA` without `skip_deployment`.
PR comment workflow changes take effect after merge. Before merge, use the branch validation workflow from a trusted upstream branch to test the changed workflow.

`/test-destroy-env` finds all core and management groups that start with `rg-<CI_ENV_PREFIX>` and have the PR's Git reference in the `ci_git_ref` tag. It includes previous naming schemes and locations in the selected subscription.
If another repository owns a selected group, the command stops. See [Forks that share a subscription](#forks-that-share-a-subscription).
For an upstream PR, it also cleans the tagged branch environments. Cleanup refuses conflicting ownership tags and shares deployment concurrency.
Scheduled cleanup continues to use the `ci_git_ref` tags. It also uses the `CI_ENV_PREFIX` name prefix and the `ci_repository` tag. Retained vaults remain subject to their existing soft-delete and purge protection policies.

### Keep a CI environment

Scheduled cleanup stops a PR or branch environment after 4 hours without activity. It destroys the environment after 48 hours, or when the PR closes or the branch is deleted.
To keep an environment, for example for a demo, add the `ci_keep_until` tag to its core group (`rg-<TRE_ID>`) or its management group (`rg-<TRE_ID>-mgmt`):

| Value | Result |
| --- | --- |
| A date, for example `2026-11-15` | Cleanup does not stop or destroy the environment until the end of that day (UTC). After that day, the normal rules apply again. |
| `forever` | Cleanup does not stop or destroy the environment until you remove the tag. |
| Any other value | Cleanup does not stop or destroy the environment, and the run shows a warning about the invalid value. |

The tag claims the environment. You are then responsible for its cost:

* Use a date, not `forever`, when you can. If you forget the tag, the date ends it.
* Stop the environment when you do not use it. Start it again when you need it.
* Remove the tag when you no longer need the environment. The next scheduled run then applies the normal rules, and destroys an environment whose PR is closed or whose branch is deleted.

Each cleanup run that keeps an environment shows a `CI cleanup keep` warning annotation with the group and the tag value.
A manual run of the cleanup workflow with `mode=cleanup` also keeps the environment.
`/test-destroy-env` ignores the tag, because it is an explicit request to destroy the environment. The tag does not apply to the main workspace cleanup.
Bootstrap and Terraform keep the tag when CI deploys the environment again.

#### Operate a kept environment from your computer

You need the Azure CLI, `bash`, `jq` and a clone of this repository. You also need Contributor access to `rg-<TRE_ID>` and its `rg-<TRE_ID>-ws-*` groups. The examples put the tag on the core group `rg-<TRE_ID>`, so that this access is sufficient.

1. Log in to the subscription that CI uses:

    ```bash
    az login --tenant <TENANT_ID>
    az account set --subscription <SUBSCRIPTION_ID>
    ```

1. Find the `TRE_ID` of the environment. The deployment log shows it:

    * A branch deployment prints `using id of: ... (TRE ID <TRE_ID>)`.
    * A `/test` run prints `CI environment <TRE_ID> in <LOCATION>` in its `Derive CI environment ID` step.

    You can also read it from the `tre_id` tag of the core group. For a PR environment, the Git reference is `refs/pull/<PR_NUMBER>/merge`:

    ```bash
    az group list -o tsv --query "[?starts_with(name, 'rg-<CI_ENV_PREFIX>') && tags.ci_git_ref=='refs/heads/<BRANCH>' && tags.tre_id].tags.tre_id"
    ```

1. Claim the environment, then stop and start it as you need:

    ```bash
    export TRE_ID=<TRE_ID>
    az group update --name "rg-${TRE_ID}" --set tags.ci_keep_until=2026-11-15
    devops/scripts/control_tre.sh stop
    devops/scripts/control_tre.sh start
    ```

1. Remove the tag when you no longer need the environment:

    ```bash
    az tag update --resource-id "$(az group show --name "rg-${TRE_ID}" --query id -o tsv)" --operation Delete --tags ci_keep_until
    ```

`control_tre.sh stop` stops the firewall, the Application Gateway, MySQL, the resource processor and the core VMs. It also deallocates all workspace VMs. `control_tre.sh start` starts the same core services, but not the workspace VMs. Start the workspace VMs from the TRE UI, or with `az vm start`.
Do not use `make tre-start` or `make tre-stop` for a CI environment. These targets load `config.yaml`, which replaces the `TRE_ID` that you give.

### Forks that share a subscription

A fork can run CI in the same Azure subscription as another repository. Set the `CI_ENV_PREFIX` repository variable in the fork to a prefix that no other Azure TRE repository uses.
The prefix has 3 characters: a lowercase letter, then 2 lowercase letters or digits. This documentation uses `frk` as an example only. Do not copy it.
Set it as a repository variable, not an environment variable, so that every job reads the same value.
The prefix replaces `tre` at the start of every CI environment name, for example `rg-frk1a2b3c4d`. The 3 characters and the 8-character hash fill the 11-character `TRE_ID` limit.

Only `microsoft/AzureTRE` has a default prefix. If `CI_ENV_PREFIX` is not set in another repository, PR deployment, branch deployment and `/test-destroy-env` stop with an error. Scheduled cleanup skips PR and branch environments and shows a `CI cleanup scope` warning. The main workspace cleanup continues.
This is by design. Set `CI_ENV_PREFIX` before a fork runs PR or branch CI for the first time.
Use a prefix other than `tre` in every fork, also in a fork with its own subscription. Storage account, container registry and Key Vault names are unique across all of Azure, so a fork with `tre` can collide with upstream PR environments in the same location.
Set `tre` in a fork only to keep the names of existing environments.

If 2 repositories use the same prefix, they get the same names for the same PR number or branch, because the name hash does not include the repository.
The `ci_repository` tag stops each CI from deleting or taking over the other's groups, so the deployment of the second repository fails. Choose a unique prefix to prevent this, also when the repositories use different subscriptions.

CI also tags new core and management resource groups with `ci_repository`, which holds the GitHub repository name. Scheduled cleanup, `/test-destroy-env` and bootstrap lease recovery:

* Select only groups that start with `rg-<prefix>`.
* Refuse groups that another repository tagged with `ci_repository`.
* Treat groups without `ci_repository` as groups from before the tag existed. A repository that uses the `tre` prefix owns these groups only if it is `microsoft/AzureTRE`.

Bootstrap also stops if the management resource group has a `ci_repository` tag for another repository. A fork that uses the `tre` prefix also stops on an untagged PR or branch management group.

The fork must also use its own main environment values: `TRE_ID`, `ACR_NAME`, `MGMT_RESOURCE_GROUP_NAME`, `MGMT_STORAGE_ACCOUNT_NAME` and `ENCRYPTION_KV_NAME`. Main deployments and the main workspace cleanup use these values directly.

If the fork has CI environments from before this change, destroy them with `/test-destroy-env` before the change reaches the fork's default branch. PR comment workflows run from the default branch.
The command from before this change has no repository check. Use it only for a PR number or branch that has no upstream environment. Leave other untagged `rg-tre` groups to the upstream scheduled cleanup.
After the change, the fork's cleanup does not select these untagged `rg-tre` groups. Do not set `CI_ENV_PREFIX` to `tre` for a short time to remove them in a shared subscription.

Merge or rebase the default branch into a fork branch before you dispatch the branch deployment workflow. An older branch creates untagged `rg-tre` groups, and the upstream cleanup treats them as upstream groups.

If you rename or transfer the repository, cleanup refuses the groups that have the old name in `ci_repository`. Delete these groups manually, or change their tag to the new name.

The `validate` mode of the cleanup workflow needs a `CI_ENV_PREFIX` other than `tre` outside `microsoft/AzureTRE`.
A repository that deploys only `main` keeps the main workspace cleanup without `CI_ENV_PREFIX`. Cleanup then selects no PR or branch environment, and the run shows a `CI cleanup scope` warning annotation. If the repository has PR or branch environments, set `CI_ENV_PREFIX` as a repository variable.

### Recover CI environments from before the tag

A repository other than `microsoft/AzureTRE` that uses the `tre` prefix cannot manage its untagged CI environments. This applies also to a fork with its own subscription. Cleanup and `/test-destroy-env` refuse these groups, and bootstrap stops on them.
To recover an environment that your repository created, tag its core and management groups with your repository name. Then run `/test-destroy-env`, or wait for the scheduled cleanup:

```bash
az group update --name rg-tre1a2b3c4d --set tags.ci_repository=contoso/AzureTRE
az group update --name rg-tre1a2b3c4d-mgmt --set tags.ci_repository=contoso/AzureTRE
```

Tag only groups that your repository created. In a shared subscription, the same name can belong to an upstream environment.

## Dockerfile build checks

The `Dockerfile Build Check` workflow builds Dockerfiles and Porter bundle images each Monday at 06:00 UTC. It can also run manually. Scheduled runs use the default branch, where the workflow must first be merged.

Pull requests to `main` or `feature/**` select targets when their Dockerfile, Porter manifest or named build context changes. Changes to the shared Porter versions, installer or build helper select all bundles. Changes to the check's workflow or scripts select all targets.

Changes within a named context source select its own bundle and every consuming bundle. These sources include the base workspace, Guacamole Windows VM and import review VM directories. Runs use the PR number for cancellation, so identical branch names in different forks remain independent.

Discovery fails if a tracked Porter bundle under `templates/` has only one of `porter.yaml` and `Dockerfile.tmpl`. Removing both files removes the bundle from the build matrix.

These checks run without Azure deployment credentials and do not publish images. Each target starts on a fresh GitHub-hosted runner without an imported build cache.

If a target fails, the job waits ten seconds and retries it once. The retry includes Porter installation and the build, with a new Porter directory to avoid an incomplete installation. Both attempts remain in the job log. A successful retry passes the build check.

The report lists every selected target. It fails if both build attempts fail, a job is cancelled, or a result is missing or invalid. Result artifacts are retained for seven days and replaced when a job runs again.

If a build fails, open its job log to identify the failed command. Package or base-image failures can occur without repository changes. The existing deployment validation remains necessary to test deployed services.

## Setup instructions

Before you can run the `deploy_tre.yml` workflow there are some one-time configuration steps that we need to do, similar to the Pre-deployment steps for manual deployment.

!!! tip
    In some of the steps below, you are asked to configure repository secrets. Follow the [GitHub guide](https://docs.github.com/en/actions/security-guides/encrypted-secrets) on creating repository secrets if you are unfamiliar with this step.

1. Create a service principal for the subscription so that the workflow can provision Azure resources.
1. Decide on a TRE ID and the location for the Azure resources
1. Create app registrations for API authentication
1. Create app registrations and a user for the E2E tests
1. Create a workspace app registration for setting up workspaces (for the E2E tests)
1. Configure repository secrets
1. Deploy the TRE using the workflow

### Create a service principal and configure OIDC authentication

1. Login to Azure

  Log in to Azure using `az login` and select the Azure subscription you wish to deploy Azure TRE to:

  ```cmd
  az login
  az account list
  az account set --subscription <subscription ID>
  ```

  See [Sign in with Azure CLI](https://docs.microsoft.com/cli/azure/authenticate-azure-cli) for more details.

1. Create a service principal

  A service principal needs to be created to authorize CI/CD workflows to provision resources for the TRE workspaces and workspace services.

  Create a main service principal with "**Owner**" role:

  ```cmd
  az ad sp create-for-rbac --name "sp-aztre-cicd" --role Owner --scopes /subscriptions/<subscription_id>
  ```

  !!! caution
      Save the output (especially the `appId` and `tenant`) - you will need it for the next steps

1. Configure federated identity credentials for GitHub Actions OIDC

  Configure the service principal to trust GitHub Actions OIDC tokens from your repository:

  ```cmd
  az ad app federated-credential create --id <APPLICATION_OBJECT_ID> --parameters credential.json
  ```

  Where `credential.json` contains (replace `OWNER`, `REPO`, and `ENVIRONMENT` with your values):

  ```json
  {
    "name": "GitHubActions",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:OWNER/REPO:environment:ENVIRONMENT",
    "description": "GitHub Actions OIDC for Azure TRE",
    "audiences": [
      "api://AzureADTokenExchange"
    ]
  }
  ```

  For the main/develop branches, you may also want to add federated credentials with subject `repo:OWNER/REPO:ref:refs/heads/main` and `repo:OWNER/REPO:ref:refs/heads/develop`.

  See [Configure a federated identity credential on an app](https://learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust?pivots=identity-wif-apps-methods-azcli) for more details.

1. Configure repository secrets for OIDC authentication

  Configure the following **secrets** (not variables) in your repository or environment:

  | <div style="width: 230px">Secret name</div> | Description |
  | ----------- | ----------- |
  | `AZURE_CLIENT_ID` | The application (client) ID of the service principal created above |
  | `AZURE_TENANT_ID` | The tenant ID where the service principal was created |
  | `AZURE_SUBSCRIPTION_ID` | The Azure subscription ID where resources will be deployed |

### Decide on a TRE ID and Azure resources location

Configure the TRE ID and LOCATION repository secrets

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `tre-dev-42` will result in a resource group name for Azure TRE instance of `rg-tre-dev-42`. This must be less than 12 characters. Allowed characters: lowercase alphanumerics. |
| `LOCATION` | The Azure location (region) for all resources. E.g. `westeurope` |

### Create app registrations for API authentication

Follow the instructions to run the **app registration script** in the [Authentication and Authorization document](../auth.md#app-registrations). Use the values for TRE ID and LOCATION from above.

Configure the TRE API and Swagger UI repository secrets

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `AAD_TENANT_ID` | The tenant ID of the Microsoft Entra ID. |
| `SWAGGER_UI_CLIENT_ID` | The application (client) ID of the TRE Swagger UI app. |
| `API_CLIENT_ID` | The application (client) ID of the TRE API app. |
| `API_CLIENT_SECRET` | The application password (client secret) of the TRE API app. |

### Create an app registration and a user for the E2E tests

Follow the instructions to [create an app registration and a test user for the E2E tests in the Authentication and Authorization](../auth.md#tre-e2e-test) document.

Configure the E2E Test repository secrets

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TEST_APP_ID` | The application (client) ID of the E2E Test app |
| `TEST_USER_NAME` | The username of the E2E Test User |
| `TEST_USER_PASSWORD` | The password of the E2E Test User |

### Create a workspace app registration for setting up workspaces (for the E2E tests)

Follow the [instructions to create a workspace app registration](../auth.md#workspaces) (used for the E2E tests) - and make the E2E test user a **WorkspaceOwner** for the app registration.

Configure the TEST_WORKSPACE_APP_ID repository secret

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TEST_WORKSPACE_APP_ID` | The application (client) ID of the Workspaces app. |
| `TEST_WORKSPACE_APP_SECRET` | The application (client) secret of the Workspaces app. |

### Configure repository/environment secrets

Configure additional secrets used in the deployment workflow:

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `tre-dev-42` will result in a resource group name for Azure TRE instance of `rg-tre-dev-42`. This must be less than 12 characters. Allowed characters: lowercase alphanumerics. |
| `MGMT_RESOURCE_GROUP_NAME` | The name of the shared resource group for all Azure TRE core resources. |
| `MGMT_STORAGE_ACCOUNT_NAME` | The name of the storage account to hold the Terraform state and other deployment artifacts. E.g. `mystorageaccount`. |
| `ACR_NAME` | A globally unique name for the Azure Container Registry (ACR) that will be created to store deployment images. |
| `CUSTOM_DOMAIN` | Optional. Custom domain name to access the Azure TRE portal. See [Custom domain name](../custom-domain.md). |


### Configure repository/environment variables

Configure variables used in the deployment workflow:

| <div style="width: 230px">Variable name</div> | Description |
| ----------- | ----------- |
| `LOCATION` | The Azure location (region) for all resources. E.g. `westeurope` |
| `TERRAFORM_STATE_CONTAINER_NAME` | Optional. The name of the blob container to hold the Terraform state. Default value is `tfstate`. |
| `CORE_ADDRESS_SPACE` | Optional. The address space for the Azure TRE core virtual network. Default value is `10.0.0.0/22`. |
| `TRE_ADDRESS_SPACE` | Optional. The address space for the whole TRE environment virtual network where workspaces networks will be created (can include the core network as well). Default value is `10.0.0.0/16` |
| `CORE_APP_SERVICE_PLAN_SKU` | Optional. The SKU used for AppService plan for core infrastructure. Default value is `P1v2`. |
| `WORKSPACE_APP_SERVICE_PLAN_SKU` | Optional. The SKU used for AppService plan used in E2E tests. Default value is `P1v2`. |
| `RESOURCE_PROCESSOR_VMSS_SKU` | Optional. The SKU of the resource processor VMSS. Defaults to `Standard_B2ls_v2`. |
| `RESOURCE_PROCESSOR_NUMBER_PROCESSES_PER_INSTANCE` | Optional. The number of processes to instantiate when the Resource Processor starts. Equates to the number of parallel deployment operations possible in your TRE. Defaults to `5`. |
| `ENABLE_SWAGGER` | Optional. Determines whether the Swagger interface for the API will be available. Default value is `false`. |
| `FIREWALL_SKU` | Optional. The SKU of the Azure Firewall instance. Default value is `Standard`. Allowed values [`Basic`, `Standard`, `Premium`]. See [Azure Firewall SKU feature comparison](https://learn.microsoft.com/en-us/azure/firewall/choose-firewall-sku). |
| `APP_GATEWAY_SKU` | Optional. The SKU of the Application Gateway. Default value is `Standard_v2`. Allowed values [`Standard_v2`, `WAF_v2`] |
| `ENABLE_CMK_ENCRYPTION` | Optional. Default is `false`, if set to `true` customer-managed key encryption will be enabled for all supported resources. |
| `CI_ENV_PREFIX` | Required outside `microsoft/AzureTRE` for PR and branch CI environments. Set it as a repository variable, not an environment variable. The 3-character prefix of PR and branch CI environment names: a lowercase letter, then 2 lowercase letters or digits. Only `microsoft/AzureTRE` has the default value `tre`. Every fork uses a prefix that no other Azure TRE repository uses, because some Azure resource names are globally unique. See [Forks that share a subscription](#forks-that-share-a-subscription). |

### Deploy the TRE using the workflow

With all the repository secrets set, you can trigger a workflow run by pushing to develop/main of your fork, or by dispatching the workflow manually.
