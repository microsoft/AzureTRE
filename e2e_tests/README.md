# End-to-end (E2E) tests

To run the E2E tests locally:

1. Navigate to the `e2e_tests` folder: `cd e2e_tests`
1. Define the following environment variables:

    | Environment variable name | Description | Example value |
    | ------------------------- | ----------- | ------------- |
    | `RESOURCE_LOCATION` | The Azure Tre deployed environment `LOCATION`. | `eastus` |
    | `TRE_ID` | The Azure TRE instance name - used for deployment of resources (can be set to anything when debugging locally). | `mytre-dev-3142` |
    | `RESOURCE` | The application (client) ID of the [TRE API](../docs/auth.md#tre-api) service principal. | |
    | `AUTH_TENANT_ID` | The tenant ID of the Azure AD. | |
    | `CLIENT_ID` | The application (client) ID of the [E2E Test app](../docs/auth.md#tre-e2e-test) service principal. | |
    | `SCOPE` | Scope(s) for the token. | `api://<TRE API app client ID>/Workspace.Read api://<TRE API app client ID>/Workspace.Write` |
    | `USERNAME` | The username of the [E2E User](../docs/auth.md#end-to-end-test-user). | |
    | `PASSWORD` | The password of the [E2E User](../docs/auth.md#end-to-end-test-user). | |
    | `AUTH_APP_CLIENT_ID` | The application (client) ID of the [workspaces app](auth.md#workspaces). | |
    | `ACR_NAME` | The name of the TRE container registry. | |

1. Run the E2E tests:

   ```bash
   PYTHONPATH=. python -m pytest --junit-xml pytest_e2e.xml
   ```
