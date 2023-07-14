# Upgrading AzureTRE version

This document will cover how AzureTRE is referenced and how to upgrade its version in the [AzureTRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment)

## Introduction

AzureTRE referenced as an external folder in [AzureTRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment) (which is used as a template for your project in the quick start guide). A specific version of AzureTRE is downloaded as part of devcontainer setup.

A symlink is then created making it available to reference in the directory itself (it is available only for reference, any changes to it are gitignored).

## How to upgrade AzureTRE version

> Please check the release notes before upgrading.

- If using the [AzureTRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment) directly (not one created using a Template), you need to git pull the latest version.

- If using a repository created from the `AzureTRE-Deployment` template then run following git command in your own repo:
```sh
git remote add upstream https://github.com/microsoft/AzureTRE-Deployment
git pull upstream main --allow-unrelated-histories
```
This will pull the latest version of AzureTRE to your copy of the repository. You may need to resovle merge conflicts if you have made edits.

Once the code is merged follow same process used to initally deploy the TRE to upgrade the TRE. This might mean running a command such as `make all`, or running your CI/CD pipeline(s).

> If running commands manually, please ensure that you build and push the container images. Running `make tre-deploy` alone will update the infrastructure but not the container images. `make all` runs all the required commands.

## Deploying a specific version of Azure TRE

If you wish to upgrade or deploy a specific version, or unreleased version of Azure TRE and are using the [AzureTRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment) you can change the value of `OSS_VERSION` in `.devcontainer/devcontainer.json`, for example:

- `"OSS_VERSION": "v0.9.0"`
- `"OSS_VERSION": "main"`
