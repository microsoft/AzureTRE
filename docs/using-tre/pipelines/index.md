# Pipelines

The AzureTRE deployment repository contains the following github workflows:

1. Build Validation - validates the code by running linter and terraform validation.
1. Clean Validation Environments - a periodical workflow to clean unused AzureTRE environments.
1. Deploy Azure TRE (branch) - This workflow is intended to be used to test workflow changes. It deploys AzureTRE using the workflows defined on the branch
1. Deploy Azure TRE - This workflow is the integration build run for pushes to the main branch. It also runs on a schedule, serving as the nightly build to keep the main AzureTRE env in sync.
1. Deploy Azure TRE Reusable - responsible to deploy AzureTRE. It is referenced in other Azure TRE deployment workflows.

The workflows are using github environment to source its environment variables. Make sure to define it in your github repository and provide it as an input for the workflows.

The following environment variables should be defined in your pipelines:

1. [Auth env vars](auth.md##create_authentication_assets)
1. [Core and Devops env vars](docs/tre-admins/environment-variables.md)

## How to Contribute to our Documentation

If you have any comments or suggestions about our documentation then you can visit our GitHub project and either raise a new issue, or comment on one of the existing ones.

You can find our existing documentation issues on GitHub by clicking on the link below:

[Existing Documentation Issues](https://github.com/microsoft/AzureTRE/issues?q=is%3Aissue+is%3Aopen+label%3Adocumentation)

Or, you can raise a new issue by clicking on this link:

[Report an Issue or Make a Suggestion](https://github.com/microsoft/AzureTRE/issues/new/choose)

**Thank you for your patience and support!**
