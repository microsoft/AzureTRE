# TRE Deployment

This document will cover how to extend AzureTRE with your custom images and deploy it.

## AzureTRE deployment repo

AzureTRE has an OSS deployment repository which you can find [here.](https://github.com/microsoft/AzureTRE-Deployment)
It contains all the required tooling to develop your custom templates and deploy the Azure TRE.

### Contents

AzureTRE deployment repository contains the following:

- Github Actions implementing AzureTRE automation, including running deployments to Azure
- Configuration specific to deployment
- Directories setup for: workspace, workspace service and user resource template definitions
- Devcontainer setup

### AzureTRE Reference

AzureTRE deployment repository allows you to reference AzureTRE as a folder, but also uses it in its deployment. See [AzureTRE deployment readme](https://github.com/microsoft/AzureTRE-Deployment/blob/main/README.md) to learn more on how to setup and upgrade AzureTRE version.

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

## CI/CD workflows

The AzureTRE deployment repository contains the following github workflows:
1. Build Validation - validates the code by running linter and terraform validation.
1. Clean Validation Environments - a periodical workflow to clean unused AzureTRE environments.
1. Deploy Azure TRE (branch) - This workflow is intended to be used to test workflow changes. It deploys AzureTRE using the workflows defined on the branch
1. Deploy Azure TRE - This workflow is the integration build run for pushes to the main branch. It also runs on a schedule, serving as the nightly build to keep the main AzureTRE env in sync.
1. Deploy Azure TRE Reusable - responsible to deploy AzureTRE. It is referenced in other Azure TRE deployment workflows.

The workflows are using github environment 
## Make commands

The Makefile in the AzureTRE deployment repository sources the make commands from AzureTRE that it references. This allows you to add your commands and also use the same make commands used in the AzureTRE.
