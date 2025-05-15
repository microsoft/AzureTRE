# Maintainers

This document is targeted at maintainers of the AzureTRE project.
For information on developing and contributing to AzureTRE, see the [TRE Developers docs](https://microsoft.github.io/AzureTRE/tre-developers/)

For information on GitHub PR Bot Commands, see the [GitHub PR Bot Commands docs](https://microsoft.github.io/AzureTRE/tre-developers/github-pr-bot-commands/)

## Periodic tasks

### [quarterly] Upgrade bundles' Terraform providers

Each bundle is using Terraform providers to deploy itself. The providers are pinned to an exact version to avoid instability and issues during investigations.

* The root module should be pinned while using ">=" for sub-modules to indicate the minimum required version.

This, however, requires us to manually update them by referencing newer versions in the provider blocks and associated lock files (`devops/scripts/upgrade_lock_files.sh` can help).
