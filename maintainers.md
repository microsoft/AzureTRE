# Maintainers

This document is targetted at Microsoft maintainers of the AzureTRE project. For information on developing with Azure TRE, see the [TRE Developers docs](https://microsoft.github.io/AzureTRE/tre-developers/)

## PR Comment bot commands

**Note** that these commands are not immediate - you need to wait for the GitHub action that performs the task to start up.

### `/help`

This command will cause the pr-comment-bot to respond with a comment listing the available commands.

### `/test`

This command runs the build, deploy and test cycle for a PR. 

**IMPORTANT**

This command works on PRs from forks, and makes the deployment secrets available. Before running tests on a PR, ensure that there are no changes in the PR that could have unintended consequences (e.g. leak secrets or perform undesirable operations in the testing subscription). 

Check for changes to anything that is run during the build/deploy/test cycle, including: 
- modifications to workflows (including adding new actions or changing versions of existing actions)
- modifications to the Makefile
- modifications to scripts
- new python packages being installed


### `/test-destroy-env`

When running `/test` multiple times on a PR, the same TRE ID and environment are used by default. The `/test-destroy-env` command destroys a previously created validation environment, allowing you to re-run `/test` with a clean starting point.

### `/test-force-approve`

This command skips running tests for a build and marks the checks as completed. This is intended to be used in scenarios where running the tests for a PR doesn't add value (for example, changing a workflow file that is always pulled from the default branch).
