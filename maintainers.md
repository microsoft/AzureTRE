# Maintainers

This document is targeted at maintainers of the AzureTRE project.
For information on developing and contributing to AzureTRE, see the [TRE Developers docs](https://microsoft.github.io/AzureTRE/tre-developers/)

## PR Comment bot commands

**Notes**
- these commands are not immediate - you need to wait for the GitHub action that performs the task to start up.
- builds triggered via these commands will use the workflow definitions from `main`. To test workflow changes before merging to `main`, the changes need to be pushed to a branch in the main repo and then the `deploy_tre_branch.yml` workflow can be run against that branch.

These commands can only be run when commented by a user who is identified as a repo collaborator (see [granting access to run commands](#granting-access-to-run-commands))

### `/help`

This command will cause the pr-comment-bot to respond with a comment listing the available commands.

### `/test [<sha>]`

This command runs the build, deploy, and smoke tests for a PR.

For PRs from maintainers (i.e. users with write access to microsoft/AzureTRE), `/test` is sufficient.

For other PRs, the checks below should be carried out. Once satisfied that the PR is safe to run tests against, you should use `/test <sha>` where `<sha>` is the SHA for the commit that you have verified.
You can use the full or short form of the SHA, but it must be at least 7 characters (GitHub UI shows 7 characters).

**IMPORTANT**

This command works on PRs from forks, and makes the deployment secrets available.
Before running tests on a PR, ensure that there are no changes in the PR that could have unintended consequences (e.g. leak secrets or perform undesirable operations in the testing subscription).

Check for changes to anything that is run during the build/deploy/test cycle, including:
- modifications to workflows (including adding new actions or changing versions of existing actions)
- modifications to the Makefile
- modifications to scripts
- new python packages being installed

### `/test-extended [<sha>]` / `/test-extended-aad [<sha>]`/ `/test-shared-services [<sha>]`

This command runs the build, deploy, and smoke & extended / shared services tests for a PR.

For PRs from maintainers (i.e. users with write access to microsoft/AzureTRE), `/test-extended` is sufficient.

If a change has been made which would affect any of the core shared services, make sure you run `/test-shared-services`.

For other PRs, the checks below should be carried out. Once satisfied that the PR is safe to run tests against, you should use `/test-extended <sha>` where `<sha>` is the SHA for the commit that you have verified.
You can use the full or short form of the SHA, but it must be at least 7 characters (GitHub UI shows 7 characters).

**IMPORTANT**

As with `/test`, this command works on PRs from forks, and makes the deployment secrets available.
Before running tests on a PR, run the same checks on the PR code as for `/test`.

### `/test-destroy-env`

When running `/test` multiple times on a PR, the same TRE ID and environment are used by default. The `/test-destroy-env` command destroys a previously created validation environment, allowing you to re-run `/test` with a clean starting point.

The `/test-destroy-env` command also destroys the environment associated with the PR branch (created by running the `deploy_tre_branch` workflow).

### `/test-force-approve`

This command skips running tests for a build and marks the checks as completed.
This is intended to be used in scenarios where running the tests for a PR doesn't add value (for example, changing a workflow file that is always pulled from the default branch).


## Granting access to run commands

Currently, the GitHub API to determine whether a user is a collaborator doesn't seem to respect permissions that a user is granted via a group. As a result, users need to be directly granted `write` permission in the repo to be able to run the comment bot commands.

## Periodic tasks

### [quarterly] Upgrade bundles' Terraform providers

Each bundle is using Terraform providers to deploy itself. The providers are set with specific versions for stability and consistency between builds.

This, however, requires us to manually update them by referencing newer versions in the provider blocks and associated lock files (`devops/scripts/upgrade_lock_files.sh` can help).
