# GitHub Actions workflows (CI/CD)

To deploy the Azure TRE using GitHub workflows, create a fork of the repository.

Deployment is done using the `/.github/workflows/deploy_tre.yml` workflow. This method is also used to deploy the dev/test environment for the original Azure TRE repository.

## Setup instructions

Before you can run the `deploy_tre.yml` pipeline there are some one-time configuration steps that we need to do, similar to the Pre-deployment steps for manual deployment.

!!! tip
    In some of the steps below, you are asked to configure repository secrets. Follow the [GitHub guide](https://docs.github.com/en/actions/security-guides/encrypted-secrets) on creating repository secrets if you are unfamiliar with this step.

1. Create a service principal for the subscription so that the workflow can provision Azure resources.
1. Decide on a TRE ID and the location for the Azure resources
1. Create app registrations for API authentication
1. Create app registrations and a user for the E2E tests
1. Create a workspace app registration for setting up workspaces (for the E2E tests)
1. Create a Teams WebHook for deployment notifications
1. Configure repository secrets
1. Deploy the TRE using the workflow

### Create a service principal for provisioning resources

1. Login to Azure

  Log in to Azure using `az login` and select the Azure subscription you wish to deploy Azure TRE to:

  ```cmd
  az login
  az account list
  az account set --subscription <subscription ID>
  ```

  !!! caution
      When running locally the credentials of the logged-in user will be used to deploy the infrastructure. Hence, it is essential that the user has enough permissions to deploy all resources.

  See [Sign in with Azure CLI](https://docs.microsoft.com/cli/azure/authenticate-azure-cli) for more details.

1. Create a service principal

  A service principal needs to be created to authorize CI/CD workflows to provision resources for the TRE workspaces and workspace services.

  Create a main service principal with "**Owner**" role:

  ```cmd
  az ad sp create-for-rbac --name "sp-aztre-core" --role Owner --scopes /subscriptions/<subscription_id> --sdk-auth
  ```

  !!! caution
      Save the JSON output locally - as you will need it later for setting secrets in the build

1. Configure the repository secrets. These values will be in the JSON file from the previous step.

  | <div style="width: 230px">Secret name</div> | Description |
  | ----------- | ----------- |
  | `ARM_SUBSCRIPTION_ID` | The Azure subscription to deploy to  |
  | `ARM_TENANT_ID` | The Azure tenant to deploy to  |
  | `ARM_CLIENT_ID` | The Azure Client Id (user)  |
  | `ARM_CLIENT_SECRET` | The Azure Client Secret (password)  |

### Decide on a TRE ID and Azure resources location

Configure the TRE ID and LOCATION repository secrets

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `TRE_ID` | A globally unique identifier. `TRE_ID` can be found in the resource names of the Azure TRE instance; for example, a `TRE_ID` of `tre-dev-42` will result in a resource group name for Azure TRE instance of `rg-tre-dev-42`. This must be less than 12 characters. Allowed characters: Alphanumeric, underscores, and hyphens. |
| `LOCATION` | The Azure location (region) for all resources. E.g. `westeurope` |

### Create app registrations for API authentication

Follow the instructions to run the **app registration script** in the [Authentication and Authorization document](../auth.md#app-registrations). Use the values for TRE ID and LOCATION from above.

Configure the TRE API and Swagger UI repository secrets

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `AAD_TENANT_ID` | The tenant ID of the Azure AD. |
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

### Create a Teams Webhook for deployment notifications

The `deploy_tre.yml` workflow sends a notification to a Microsoft Teams channel when it finishes running.

!!! note
    If you don't want to notify a channel, you can also remove the **Notify dedicated teams channel** steps in the pipeline

1. Follow the [Microsoft Docs](https://docs.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook) to create a webhook for your channel

1. Configure the MS_TEAMS_WEBHOOK_URI repository secret

  | <div style="width: 230px">Secret name</div> | Description |
  | ----------- | ----------- |
  | `MS_TEAMS_WEBHOOK_URI` | URI for the Teams channel webhook |

### Configure repository secrets

Configure additional repository secrets used in the deployment pipeline

| <div style="width: 230px">Secret name</div> | Description |
| ----------- | ----------- |
| `MGMT_RESOURCE_GROUP` | The name of the shared resource group for all Azure TRE core resources. |
| `STATE_STORAGE_ACCOUNT_NAME` | The name of the storage account to hold the Terraform state and other deployment artifacts. E.g. `mystorageaccount`. |
| `TF_STATE_CONTAINER` | The name of the blob container to hold the Terraform state. By convention the value is `tfstate`. |
| `ACR_NAME` | A globally unique name for the Azure Container Registry (ACR) that will be created to store deployment images. |
| `CORE_ADDRESS_SPACE` |  The address space for the Azure TRE core virtual network. E.g. `10.1.0.0/22`. Recommended `/22` or larger.  |
| `TRE_ADDRESS_SPACE` | The address space for the whole TRE environment virtual network where workspaces networks will be created (can include the core network as well). E.g. `10.0.0.0/12`|
| `DEPLOY_GITEA` | If set to `false` disables deployment of the Gitea shared service. |
| `DEPLOY_NEXUS` | If set to `false` disables deployment of the Nexus shared service. |

### Deploy the TRE using the workflow

With all the repository secrets set, you can trigger a workflow run by pushing to develop/main of your fork, or by dispatching the workflow manually.

## Pull request security

Many of the workflows access [GitHub repository secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets) and malicious code in workflows pose a security risk. Thus, pull requests (PRs) from forks cannot be allowed to execute workflows freely. By default, workflows are not run by pull requests from forks, but can be enabled with [`pull_request_target` event](https://docs.github.com/en/actions/learn-github-actions/events-that-trigger-workflows#pull_request_target).

However, changes reviewed and found safe should be able to execute workflows. A label, that can only be assigned by authorized project members, can be used to safeguard workflow execution:

```yaml
on:
  pull_request_target:
    types: [labeled]
    branches: [main]

jobs:
  my_job:
    if: |
      github.event.pull_request.head.repo.full_name == github.repository
      || contains(github.event.pull_request.labels.*.name, 'safe to test')
```

The snippet above contains two conditions:

1. Checking the name of the originating repository of the PR. In case the PR is from a fork the condition evaluates to `false`. `github.repository` (see [`github` context](https://docs.github.com/en/actions/learn-github-actions/contexts#github-context)) evaluates into string e.g., "microsoft/AzureTRE".
2. Checking if the pull request has a label "safe to test".

Effectively, the two conditions allow the job execution for all PRs originating from internal branches, but only allow PRs originating from a fork with "safe to test" label assigned to do so. The workflows of fork PRs will remain in "skipped" state until the label is set.

!!! caution
    Any job **without** the condition is allowed to execute even if the PR originates from a fork.
