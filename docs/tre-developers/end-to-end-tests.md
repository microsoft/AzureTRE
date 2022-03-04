# End-to-end (E2E) tests

## Prerequisites

1. Authentication and Authorization configuration set up as noted [here](../tre-admins/auth.md)
1. An Azure Tre deployed environment.

## Debugging the End-to-End tests

Use the 'Run and Debug' icon within Visual Studio Code and chose "E2E Extended" in the drop down box and click play.

- This will copy /workspaces/AzureTRE/templates/core/.env to /workspaces/AzureTRE/e2e_tests/.env for you which supplies your authentciation details

- This will also use /workspaces/AzureTRE/templates/core/private.env file for other values.

## Running the End-to-End tests locally

1. Navigate to the `e2e_tests` folder: `cd e2e_tests`
1. Define the following environment variables:

    | Environment variable name | Description | Example value |
    | ------------------------- | ----------- | ------------- |
    | `RESOURCE_LOCATION` | The Azure Tre deployed environment `LOCATION`. | `eastus` |
    | `TRE_ID` | The Azure TRE instance name - used for deployment of resources (can be set to anything when debugging locally). | `mytre-dev-3142` |
    | `API_CLIENT_ID` | The application (client) ID of the [TRE API](../tre-admins/auth.md#tre-api) service principal. | |
    | `AAD_TENANT_ID` | The tenant ID of the Azure AD. (This could be different to the tenant the subscription is linked to)| |
    | `CLIENT_ID` | The application (client) ID of the [E2E Test app](../tre-admins/auth.md#tre-e2e-test) service principal. | |
    | `USERNAME` | The username of the [E2E User](../tre-admins/auth.md#end-to-end-test-user). | |
    | `PASSWORD` | The password of the [E2E User](../tre-admins/auth.md#end-to-end-test-user). | |
    | `TEST_WORKSPACE_APP_ID` | The application (client) ID of the [workspaces app](../tre-admins/auth.md#workspaces). | |

1. Run the E2E tests:

   ```bash
   make test-e2e-smoke
   ```
   or
   ```bash
   make test-e2e-extended
   ```
