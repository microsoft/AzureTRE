# Upgrading AzureTRE version

This document will cover how Azure TRE is referenced and how to upgrade its version in the [Azure TRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment)

## Introduction

Azure TRE is referenced as an external folder in the [Azure TRE deployment repository](https://github.com/Microsoft/AzureTRE-Deployment) (which is used as a template for your project in the quick start guide). A specific version of Azure TRE is downloaded as part of the devcontainer setup.

A symlink is then created making it available to reference in the directory itself (it is available only for reference, any changes to it are gitignored).

## How to upgrade the Azure TRE version

> Please check the release notes before upgrading.

- If using the [Azure TRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment) directly (not one created using a Template), you need to git pull the latest version.

- If using a repository created from the `AzureTRE-Deployment` template, then run the following git commands in your own repo:
```sh
git remote add upstream https://github.com/Microsoft/AzureTRE-Deployment
git pull upstream main --allow-unrelated-histories
```
This will pull the latest version of AzureTRE to your copy of the repository. You may need to resolve merge conflicts if you have made edits.
The `git remote add` command is only necessary the first time you upgrade your TRE version. After the first time, you only need to execute the `git pull` command.

Once the code is merged, follow the same process used to initially deploy the TRE to upgrade the TRE. This might mean running a command such as `make all`, or running your CI/CD pipeline(s).

> If running commands manually, please ensure that you build and push the container images. Running `make tre-deploy` alone will update the infrastructure but not the container images. `make all` runs all the required commands.

## Deploying a specific version of Azure TRE

If you wish to upgrade or deploy a specific version, or unreleased version of Azure TRE and are using the [Azure TRE deployment repository](https://github.com/Microsoft/AzureTRE-Deployment) you can change the value of `UPSTREAM_REPO_VERSION` in `.devcontainer/devcontainer.json`, for example:

- `"UPSTREAM_REPO_VERSION": "v0.9.0"` (to use the specified tag; be sure to specify the complete tag name (prefixed with `v` and not the release name))
- `"UPSTREAM_REPO_VERSION": "main"` (to use the latest code in the `main` branch)
- `"OSS_VERSION": "1c6ff35ec9246e53b86e93b9da5b97911edc71c1"` (to use the code at the time of the commit identified by the hash)

## Deploying a fork of Azure TRE

If you wish to deploy the Azure TRE from a forked repository you can change the values of `UPSTREAM_REPO` and `UPSTREAM_REPO_VERSION` in `.devcontainer/devcontainer.json`, for example, change:

- `"UPSTREAM_REPO": "microsoft/AzureTRE"` (the default)
- `"UPSTREAM_REPO": "myorg/AzureTRE"` (to point to a fork of the Azure TRE in your GitHub organisation)

When changing `UPSTREAM_REPO` ensure the `UPSTREAM_REPO_VERSION` variable refers to a GitHub ref on your repository fork.
