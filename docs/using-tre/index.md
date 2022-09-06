# Using TRE for Research

This documentation part will cover how to use AzureTRE, extend it with your custom images and deploy it.

## AzureTRE deployment repo

AzureTRE has an OSS deployment repository which you can find [here.](https://github.com/microsoft/AzureTRE-Deployment)
It contains all the required tooling to develop your custom templates and deploy the Azure TRE:

- Github Actions implementing AzureTRE automation, including running deployments to Azure
- Configuration specific to deployment
- Directories setup for: workspace, workspace service and user resource template definitions
- Devcontainer setup

### AzureTRE Reference

AzureTRE deployment repository allows you to reference AzureTRE as a folder, but also uses it in its deployment. See [AzureTRE deployment readme](https://github.com/microsoft/AzureTRE-Deployment/blob/main/README.md) to learn more about it.

## Getting Started

To get started with AzureTRE follow the next steps:

1. Go to [AzureTRE Deployment repository]((https://github.com/microsoft/AzureTRE-Deployment))
1. Click on use this template to set up your project from this template:

[![Use AzureTRE Deployment template](../assets/using-tre/use_template.png)](../assets/using-tre/use_template.png)

1. Follow the steps in this [Github templates guide](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) to set up the repo.
1. Having the project setup in your account, follow the next steps and guides to setup and extend AzureTRE in your environment:
    - [Local Development](local-development/index.md)
    - Setup [CI/CD pipelines](pipelines/index.md)
    - Add your [custom templates](templates/index.md)

## How to Contribute to our Documentation

If you have any comments or suggestions about our documentation then you can visit our GitHub project and either raise a new issue, or comment on one of the existing ones.

You can find our existing documentation issues on GitHub by clicking on the link below:

[Existing Documentation Issues](https://github.com/microsoft/AzureTRE/issues?q=is%3Aissue+is%3Aopen+label%3Adocumentation)

Or, you can raise a new issue by clicking on this link:

[Report an Issue or Make a Suggestion](https://github.com/microsoft/AzureTRE/issues/new/choose)

**Thank you for your patience and support!**
