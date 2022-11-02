# Upgrading AzureTRE version

This document will cover how AzureTRE is referenced and how to upgrade its version in the [AzureTRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment)

## Introduction

AzureTRE referenced as an external folder in [AzureTRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment) (which is used as a template for your project in the quick start guide). A specific version of AzureTRE is downloaded as part of devcontainer setup.
 A symlink is then created making it available to reference in the directory itself (it is available only for reference, any changes to it are gitignored)

## How to upgrade AzureTRE version

Select AzureTRE version:
1. In AzureTRE go to releases:
    ![Go to AzureTRE releases](../assets/using-tre/select_release.png)
1. Choose a release version

To upgrade AzureTRE version inside [AzureTRE deployment repository](https://github.com/microsoft/AzureTRE-Deployment):
1. Go to devcontainer.json file
1. Update the OSS_VERSION param to the desired version.

    ![Upgrade TRE Version](../../assets/using-tre/upgrade_tre_version.png)



## How to Contribute to our Documentation

If you have any comments or suggestions about our documentation then you can visit our GitHub project and either raise a new issue, or comment on one of the existing ones.

You can find our existing documentation issues on GitHub by clicking on the link below:

[Existing Documentation Issues](https://github.com/microsoft/AzureTRE/issues?q=is%3Aissue+is%3Aopen+label%3Adocumentation)

Or, you can raise a new issue by clicking on this link:

[Report an Issue or Make a Suggestion](https://github.com/microsoft/AzureTRE/issues/new/choose)

**Thank you for your patience and support!**
