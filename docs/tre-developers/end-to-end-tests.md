# End-to-end (E2E) tests

## Create Workspace Application for E2E tests

End-to-end tests require a Microsoft Entra ID application to represent the workspace API of the workspaces created during testing. This application must be created manually prior to running the tests.

Example on how to run the script:

```bash
  ./devops/scripts/aad/create_workspace_application.sh \
    --name "Workspace Application for E2E Tests" \
    --application-admin-clientid "${APPLICATION_ADMIN_CLIENT_ID}"
```

The Workspace Application ID then needs adding to the `e2e_tests/.env` file under the `TEST_WORKSPACE_APP_ID` property.

## Registering bundles to run End-to-end tests

End-to-end tests depend on certain bundles to be registered within the TRE API.

When End-to-end tests run in CI, they are registered as a prerequisite to running tests.

When running tests locally, use the `prepare-for-e2e` Makefile target:

```cmd
make prepare-for-e2e
```

## Debugging the End-to-End tests

Use the "Run and Debug" panel within Visual Studio Code, select "E2E Extended", "E2E Smoke" or "E2E Performance" in the drop down box and click play.

- This will copy `config.yaml` settings to `/workspaces/AzureTRE/e2e_tests/.env` for you which supplies your authentciation details

- This will also use `/workspaces/AzureTRE/core/private.env` file for other values.
