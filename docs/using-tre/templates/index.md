# Creating Custom templates

This document will show how to create custom templates and integrate them into your CI/CD pipelines.

## Templates types

There are 3 types of templates:

1. Workspace
1. Workspace Service
1. User Resource

Read more about them [here](../../index.md#workspace)

## How to add custom templates

AzureTRE deployment repository has directories set up for workspace, workspace service and user resource template definitions.

See the [template authoring guide](../../tre-workspace-authors/authoring-workspace-templates.md) to learn more about how to author templates.

**To add your custom templates follow the next steps:**

1. Add your template under the relevant folder (For example: if you are adding a new workspace template then place it under `/templates/workspaces` folder).  
1. Use existing templates in AzureTRE as a reference.  
1. Add porter configuration - AzureTRE uses [Porter](https://porter.sh/) as a solution for implementing and deploying workspaces and workspace, learn more about how it is used in AzureTRE [here](https://microsoft.github.io/AzureTRE/latest/tre-developers/resource-processor/#porter).  
1. Add terraform scripts to set up your deployment plan.
   - Define resource template in the API - follow [this readme](https://microsoft.github.io/AzureTRE/latest/tre-admins/registering-templates/) to register your template.
   - Use the [AzureTRE UI](https://microsoft.github.io/AzureTRE/latest/tre-developers/ui/) to deploy your resources
   - Add your custom templates to CI/CD workflows - in Deploy Azure TRE Reusable workflow make sure to add your bundles under register_bundles and publish_bundles steps.

## Publish and Register Custom templates in the CI/CD

See the [pipelines documentation](../../tre-admins/setup-instructions/cicd-deployment.md) to learn more about publishing and registering your custom templates as part of the CI/CD/

## How to Contribute to our Documentation

If you have any comments or suggestions about our documentation then you can visit our GitHub project and either raise a new issue or comment on one of the existing ones.

You can find our existing documentation issues on GitHub by clicking on the link below:

[Existing Documentation Issues](https://github.com/microsoft/AzureTRE/issues?q=is%3Aissue+is%3Aopen+label%3Adocumentation)

Or, you can raise a new issue by clicking on this link:

[Report an Issue or Make a Suggestion](https://github.com/microsoft/AzureTRE/issues/new/choose)

**Thank you for your patience and support!**
