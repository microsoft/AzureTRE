# Creating Custom templates

## How to add custom templates

AzureTRE deployment repository has directories setup for: workspace, workspace service and user resource template definitions.

**To add your custom templates follow the next steps:**
- Deployment requirements
    1. Add your template under relevant folder (For example: if you are adding a new workspace template then place it under /templates/workspaces folder).
    1. Use existing templates in AzureTRE as a reference.
    1. Add porter configuration - AzureTRE uses [Porter](https://porter.sh/) as a solution for implementing and deploying workspaces and workspace, learn more about how it is used in AzureTRE [here](https://microsoft.github.io/AzureTRE/tre-developers/resource-processor/#porter).
    1. Add terraform scripts to setup your deployment plan.
- Define resource template in the API - follow [this readme](https://microsoft.github.io/AzureTRE/tre-admins/registering-templates/) to register your template.
- Use the [AzureTRE UI](https://microsoft.github.io/AzureTRE/tre-developers/ui/) to deploy your resources
- Add your custom templates to CI/CD workflows - in Deploy Azure TRE Reusable workflow make sure to add your bundles under register_bundles and publish_bundles steps.


## How to Contribute to our Documentation

If you have any comments or suggestions about our documentation then you can visit our GitHub project and either raise a new issue, or comment on one of the existing ones.

You can find our existing documentation issues on GitHub by clicking on the link below:

[Existing Documentation Issues](https://github.com/microsoft/AzureTRE/issues?q=is%3Aissue+is%3Aopen+label%3Adocumentation)

Or, you can raise a new issue by clicking on this link:

[Report an Issue or Make a Suggestion](https://github.com/microsoft/AzureTRE/issues/new/choose)

**Thank you for your patience and support!**
