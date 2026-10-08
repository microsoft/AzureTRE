# End-to-end (E2E) tests

## Prerequisites

1. Authentication and Authorization configuration set up as noted in the [Authentication documentation](../tre-admins/auth.md)
1. An Azure Tre deployed environment.

## Registering bundles to run End-to-end tests

End-to-end tests depend on certain bundles to be registered within the TRE API.

When End-to-end tests run in CI, they are registered as a prerequisite to running tests.

When running tests locally, use the `prepare-for-e2e` Makefile target:

```cmd
make prepare-for-e2e
```

## Foundry tests

Foundry template checks belong to the smoke suite.
The install, upgrade and removal test belongs to `extended_aad` and `workspace_services`.
The existing main-push and nightly selectors include `extended_aad`.

Run only the Foundry template and lifecycle tests with:

```bash
make test-e2e-custom SELECTOR=foundry
```

The lifecycle test creates a separate Automatic-auth workspace with groups enabled and a model at capacity 1.
It keeps public access and API keys disabled.
Check the [Foundry prerequisites and validation boundaries](../tre-templates/workspace-services/ai-foundry.md#validation-before-approval) before running it.

PR comment commands use workflow definitions from `main`.
Before new bundle-registration changes reach `main`, use the branch deployment workflow with `e2eTestsCustomSelector=foundry`.
See [PR bot commands](github-pr-bot-commands.md) for the required repository access.

## Debugging the End-to-End tests

Use the "Run and Debug" panel within Visual Studio Code, select "E2E Extended", "E2E Smoke" or "E2E Performance" in the drop down box and click play.

- This will copy `config.yaml` settings to `/workspaces/AzureTRE/e2e_tests/.env` for you which supplies your authentication details

- This will also use `/workspaces/AzureTRE/core/private.env` file for other values.
