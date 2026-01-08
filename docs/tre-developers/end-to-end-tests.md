# End-to-end (E2E) tests

## Registering bundles to run End-to-end tests

End-to-end tests depend on certain bundles to be registered within the TRE API.

When End-to-end tests run in CI, they are registered as a prerequisite to running tests.

When running tests locally, use the `prepare-for-e2e` Makefile target:

```cmd
make prepare-for-e2e
```

## Manually created workspace application for targeted tests

Most E2E suites now rely on automatically created workspace applications, so you no longer need to provision a manual app registration for standard runs.

The `test_manually_created_application_owner_token` test (included in the `extended` marker set) exercises the manual-authentication flow. Its fixture automatically runs `devops/scripts/aad/create_workspace_application.sh` to create or reuse a workspace application before deploying the test workspace.

Ensure `az` CLI is installed, you are logged in to the correct tenant (`az login -t <tenant>`), and `APPLICATION_ADMIN_CLIENT_ID` (the application admin app registration) is configured so the script can add the necessary owner.

Run `make test-e2e-custom SELECTOR='manual_app'` to exercise the same flow.

## Debugging the End-to-End tests

Use the "Run and Debug" panel within Visual Studio Code, select "E2E Extended", "E2E Smoke" or "E2E Performance" in the drop down box and click play.

- This will copy `config.yaml` settings to `/workspaces/AzureTRE/e2e_tests/.env` for you which supplies your authentciation details

- This will also use `/workspaces/AzureTRE/core/private.env` file for other values.
