# AzureTRE Deployment repo

AzureTRE has an OSS deployment repository which you can find [here.](https://github.com/microsoft/AzureTRE-Deployment)
It contains all the required tooling to develop your custom templates and deploy the Azure TRE:

- Github Actions implementing AzureTRE automation, including running deployments to Azure
- Configuration specific to deployment
- Directories setup for: workspace, workspace service and user resource template definitions
- Devcontainer setup

## Create your own copy of the Azure TRE deployment repo

To get started with AzureTRE follow the next steps:

!!! note
  The following steps in this guide should be done using the deployment repo.

1. Go to [AzureTRE Deployment repository](https://github.com/microsoft/AzureTRE-Deployment)
1. Click on use this template to set up your project from this template:

    [![Use AzureTRE Deployment template](../../assets/using-tre/use_template.png)](../../assets/using-tre/use_template.png)

1. Follow the steps in this [Github templates guide](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) to set up the repo.

## Clone the Azure TRE Deployment git repository

!!! tip
    If using Windows please clone the repository to a Linux file system, i.e. to `/xxx` rather than `c:\`, for example within Windows Subsytem for Linux. If you clone the repository to a Windows file system you will likely hit issues with file permissions as described in this issue: <https://github.com/microsoft/AzureTRE/issues/1395>

  ```cmd
  git clone https://github.com/<your_username>/AzureTRE-Deployment.git
  ```

1. Open the cloned repository in Visual Studio Code and connect to the development container.

  ```cmd
  code .
  ```

!!! tip
    Visual Studio Code should recognize the available development container and ask you to open the folder using it. For additional details on connecting to remote containers, please see the [Open an existing folder in a container](https://code.visualstudio.com/docs/remote/containers#_quick-start-open-an-existing-folder-in-a-container) quickstart.

When you start the development container for the first time, the container will be built. This usually takes a few minutes. **Please use the development container for all further steps.**

## Next steps

* [AD Tenant Choices](./ad-tenant-choices.md)
