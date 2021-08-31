# Testing

## Unit tests

The unit tests are written with pytest and located in folders:

- [Management API](../management_api_app/README.md) unit tests: `/management_api_app/tests_ma/`

> The folders containing the unit tests cannot have the same name. Otherwise, pytest will get confused, when trying to run all tests in the root folder.

Run all unit tests with the following command in the root folder of the repository:

```cmd
pytest --ignore=e2e_tests
```

## End-to-end tests

To run the E2E tests locally:

1. Enter the e2e_tests directory: `cd e2e_tests`
1. Define the following environment variables:

| Environment variable name | Description |
| ------------------------- | ----------- |
| `RESOURCE_LOCATION` | The Azure Tre deployed environment `LOCATION`. Example: eastus |
| `TRE_ID` | The Azure TRE instance name - used for deployment of resources (can be set to anything when debugging locally). Example value: `mytre-dev-3142` |
| `RESOURCE` | The application (client) ID of the [TRE API](auth.md#tre-api) service principal. |
| `AUTH_TENANT_ID` | The tenant ID of the Azure AD. |
| `CLIENT_ID` | The application (client) ID of the [E2E Test app](auth.md#tre-e2e-test) service principal. |
| `USERNAME` | The username of the [E2E User](auth.md#end-to-end-test-user). |
| `PASSWORD` | The password of the [E2E User](auth.md#end-to-end-test-user). |
| `AUTH_APP_CLIENT_ID` | The application (client) ID of the [Workspaces app](auth.md#workspaces). |
| `ACR_NAME` | The Azure Tre ACR. |

1. Run the e2e tests:
   
   ```bash
   PYTHONPATH=. python -m pytest --junit-xml pytest_e2e.xml
   ```
