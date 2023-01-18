# Upgrading AzureTRE version

This document will cover how AzureTRE is referenced and how to upgrade its version in the [AzureTRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment)

## Introduction

AzureTRE referenced as an external folder in [AzureTRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment) (which is used as a template for your project in the quick start guide). A specific version of AzureTRE is downloaded as part of devcontainer setup.

A symlink is then created making it available to reference in the directory itself (it is available only for reference, any changes to it are gitignored).

## How to upgrade AzureTRE version

> Please check the release note before upgrading.

To upgrade AzureTRE version inside [AzureTRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment), you need to git pull the latest version.

Use the following git command in your `AzureTRE deployment` folder:
```
git remote add upstream https://github.com/microsoft/AzureTRE-Deployment
git pull upstream main --allow-unrelated-histories
```
This will pull the latest version of AzureTRE.
Now rebuild your container.
