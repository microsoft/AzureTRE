# GitHub PR Bot Commands

## PR Comment bot commands

**Notes**
- these commands are not immediate - you need to wait for the GitHub action that performs the task to start up.
- builds triggered via these commands will use the workflow definitions from `main`. To test workflow changes before merging to `main`, the changes need to be pushed to a branch in the main repo and then the `deploy_tre_branch.yml` workflow can be run against that branch.

These commands can only be run when commented by a user who is identified as a repo collaborator (see [granting access to run commands](#granting-access-to-run-commands))

### Test scope

Each test command builds and deploys the environment and runs smoke tests, unless the documented exception applies.
The table describes the selected assertions. A passing command does not prove every bundle or lifecycle action.

| Command | Selected tests | Coverage limit |
| --- | --- | --- |
| `/test` | API health and template checks | No bundle lifecycle proof. Documentation-only changes receive a waiver. |
| `/test-extended` | Guacamole with a Windows VM, unrestricted workspace and import review workspace | Three selected cases. The suite excludes Linux VMs and the general workspace-service cases. |
| `/test-extended-aad` | Guacamole deployment and authentication redirect in an automatically configured Entra workspace | No full identity or permissions audit. |
| `/test-shared-services` | Firewall changes and restoration, selected service lifecycles, and the combined certificate/Nexus case | Nexus requires EULA consent. A skipped certificate case provides no lifecycle proof. |
| `/test-airlock` | Import requests, access checks, the import review VM flow and export request storage routing | No export review VM or migration proof. |
| `/test-backups` | Base workspace deployment with backups enabled and disabled | No backup restore or retention proof. |

The `workspace_services`, `linux_vm` and `airlock_validation` markers have no dedicated slash command.
Use the branch workflow or the local test runner for these selections.
The `airlock_validation` marker selects two Airlock cases. It does not select the full `airlock` suite.
See [bundle selection](end-to-end-tests.md#validate-one-bundle) for exact cases and declared coverage gaps.

### Environment and evidence

Commands for the same Git reference share a deployment queue. Separate references can use separate environments.
Before parallel runs, check Azure capacity and shared dependencies.
PR-comment runs and branch-workflow runs use different environment identities.

Record the checked-out commit, run URL, selected cases, skips and cleanup result.
When using `skip_deployment`, also record the deployed version. The test commit does not prove which version is deployed.
A waiver, successful build or successful collection is not an executed E2E result.

### `/help`

This command will cause the pr-comment-bot to respond with a comment listing the available commands.

### `/test [<sha>] [skip_deployment]`

This command runs the build, deploy, and smoke tests for a PR.

For PRs from maintainers (i.e. users with write access to microsoft/AzureTRE), `/test` is sufficient.

For other PRs, the checks below should be carried out. Once satisfied that the PR is safe to run tests against, you should use `/test <sha>` where `<sha>` is the SHA for the commit that you have verified.
You can use the full or short form of the SHA, but it must be at least 7 characters (GitHub UI shows 7 characters).

If the PR validation environment is already deployed, add `skip_deployment` to skip the build and deployment jobs and run the smoke tests against the existing environment. For PRs from forks, include both the SHA and `skip_deployment`, for example `/test <sha> skip_deployment`.

The `skip_deployment` flag is only supported by `/test` and `/test-extended`.

**IMPORTANT**

This command works on PRs from forks, and makes the deployment secrets available.
Before running tests on a PR, ensure that there are no changes in the PR that could have unintended consequences (e.g. leak secrets or perform undesirable operations in the testing subscription).

Check for changes to anything that is run during the build/deploy/test cycle, including:
- modifications to workflows (including adding new actions or changing versions of existing actions)
- modifications to the Makefile
- modifications to scripts
- new python packages being installed

### `/test-extended [<sha>] [skip_deployment]` / `/test-extended-aad [<sha>]`

These commands run the build, deployment, smoke tests and selected extended tests for a PR.

For PRs from maintainers (i.e. users with write access to microsoft/AzureTRE), `/test-extended` is sufficient.

For other PRs, the checks below should be carried out. Once satisfied that the PR is safe to run tests against, you should use `/test-extended <sha>` where `<sha>` is the SHA for the commit that you have verified.
You can use the full or short form of the SHA, but it must be at least 7 characters (GitHub UI shows 7 characters).

If the PR validation environment is already deployed, add `skip_deployment` to `/test-extended` to skip the build and deployment jobs and run the smoke and extended tests against the existing environment. For PRs from forks, include both the SHA and `skip_deployment`, for example `/test-extended <sha> skip_deployment`.

The `skip_deployment` flag is not supported by `/test-extended-aad`.

**IMPORTANT**

As with `/test`, this command works on PRs from forks, and makes the deployment secrets available.
Before running tests on a PR, run the same checks on the PR code as for `/test`.

### `/test-shared-services [<sha>] accept_nexus_eula`

This command builds and deploys the PR environment, then runs smoke and shared-service tests, including the certificate and Nexus lifecycle case.
Review the PR code using the same checks as for `/test` before running it. For an external PR, include the reviewed head SHA.

The shared-service suite creates Nexus and requires explicit acceptance of the [Sonatype Nexus Community Edition EULA](https://links.sonatype.com/products/nxrm/ce-eula).
After accepting the EULA, add the exact `accept_nexus_eula` flag on the command's first line, for example `/test-shared-services <sha> accept_nexus_eula`.
Omitting the flag prevents deployment and tests. The command does not support `skip_deployment`.

For local execution, set `TEST_ACCEPT_NEXUS_EULA=true` before running the selected tests.
For the branch workflow, set the boolean `acceptNexusEula` input to `true` and select `shared_services`.
Without consent, the Nexus case fails before changing Nexus or certificate resources. The existing weekend certificate precaution still skips that case after consent is checked.
A skipped case does not prove the Nexus lifecycle.

For manual runs of `deploy_tre.yml` on `main`, use its `acceptNexusEula` input.
For recurring main runs, an administrator can record consent with the repository variable `NEXUS_EULA_ACCEPTED=true`.
Either setting supplies consent. Without either setting, scheduled/manual main runs exclude the `nexus` case and retain the other shared-service tests.
Push runs retain their existing extended/AAD selection. An excluded Nexus case provides no Nexus lifecycle evidence.

Shared-service tests allow one hour for prior-resource recovery, one hour for provisioning and one hour for each new resource's cleanup.
Nexus and certificate recovery share the first deadline. Test watchdogs include a further 30-minute margin, including failed-create cleanup.
To permit the certificate case at weekends, set `runCertificateTestsOnWeekends=true` in the branch workflow.

The reusable workflow collects the selected cases and gives Nexus a separate five-hour job.
The other cases run in their own job. These jobs run sequentially against the same environment, including when a group fails.
Empty groups are omitted. Invalid or empty selections fail planning. Each job verifies the planned checkout and exact cases before execution.

Slash commands use workflows from `main`. Before these routing changes reach `main`, validate the E2E path through `deploy_tre_branch.yml` on the reviewed upstream branch.

### `/test-airlock [<sha>]`

This command builds and deploys the PR environment, then runs smoke tests and the `airlock` selection.
Review the code with the same checks as for `/test`. For an external PR, include the reviewed head SHA.
The command does not support `skip_deployment`.

The review VM needs Nexus. Use a suitable deployed Nexus service, or use the branch workflow with `acceptNexusEula=true`.
The Airlock slash command does not accept the `accept_nexus_eula` flag.

### `/test-backups [<sha>]`

This command runs the build, deploy, and backup tests for a PR.

Use this command when a change has been made that could affect workspace backup functionality.

For PRs from maintainers (i.e. users with write access to microsoft/AzureTRE), `/test-backups` is sufficient.

For other PRs, the checks below should be carried out. Once satisfied that the PR is safe to run tests against, you should use `/test-backups <sha>` where `<sha>` is the SHA for the commit that you have verified.
You can use the full or short form of the SHA, but it must be at least 7 characters (GitHub UI shows 7 characters).

**IMPORTANT**

As with `/test`, this command works on PRs from forks, and makes the deployment secrets available.
Before running tests on a PR, run the same checks on the PR code as for `/test`.

### `/test-destroy-env`

When running `/test` multiple times on a PR, the same TRE ID and environment are used by default. The `/test-destroy-env` command destroys a previously created validation environment, allowing you to re-run `/test` with a clean starting point.

The `/test-destroy-env` command also destroys the environment associated with the PR branch (created by running the `deploy_tre_branch` workflow).

### `/test-force-approve`

This command records a waiver and marks the checks as completed. It does not run tests.
This is intended to be used in scenarios where running the tests for a PR doesn't add value (for example, changing a workflow file that is always pulled from the default branch).


## Granting access to run commands

Currently, the GitHub API to determine whether a user is a collaborator doesn't seem to respect permissions that a user is granted via a group. As a result, users need to be directly granted `write` permission in the repo to be able to run the comment bot commands.
