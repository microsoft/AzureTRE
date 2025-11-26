# End-to-end (E2E) tests

## Prerequisites

1. Authentication and Authorization configuration set up as noted [here](../tre-admins/auth.md)
1. An Azure Tre deployed environment.

## Add Automation Admin Application as Owner of Workspace Application
For the end-to-end tests to be able to create and manage workspaces, the Automation Admin Application created as part of the auth setup needs to be added as an Owner of the Workspace Application(s) used by the TRE.

You can do this using the Azure Portal, or by using the helper script `./devops/scripts/aad/add_automation_admin_to_workspace_application.sh`. For example:

```bash
  ./devops/scripts/aad/add_automation_admin_to_workspace_application.sh \
    --workspace-application-clientid "${WORKSPACE_API_CLIENT_ID}"
```

The script automatically reads the automation admin client ID from `config.yaml` (authentication.test_account_client_id).

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
