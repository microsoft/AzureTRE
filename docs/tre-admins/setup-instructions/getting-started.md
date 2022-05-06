# Getting started

## Prerequisites

To deploy an Azure TRE instance, the following assets and tools are required:

* [Azure subscription](https://azure.microsoft.com)
* [Azure Active Directory (AAD)](https://docs.microsoft.com/azure/active-directory/fundamentals/active-directory-whatis) tenant in which you can create application registrations
* Git client such as [Git](https://git-scm.com/) or [GitHub Desktop](https://desktop.github.com/)
* [Docker Desktop](https://www.docker.com/products/docker-desktop)

## Development container

The Azure TRE solution contains a [development container](https://code.visualstudio.com/docs/remote/containers) with all the required tooling to develop and deploy the Azure TRE. To deploy an Azure TRE instance using the provided development container you will also need:

* [Visual Studio Code](https://code.visualstudio.com)
* [Remote containers extension for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

The files for the dev container are located in `/.devcontainer/` folder.

!!! tip
    An alternative of running the development container locally is to use [GitHub Codespaces](https://docs.github.com/en/codespaces).

## Clone the Azure TRE Git repository

1. Clone the Azure TRE Git repository on GitHub to your local computer.

  ```cmd
  git clone https://github.com/microsoft/AzureTRE.git
  ```

  The Git repository will host some basic configuration for the TRE instances that are deployed from a given repository. Create a new branch for the instance that you are about to deploy.

  ```cmd
  cd AzureTRE
  git checkout -b quickstartenv
  ```

1. Open the cloned repository in Visual Studio Code and connect to the development container.

  ```cmd
  code .
  ```

!!! tip
    Visual Studio Code should recognize the available development container and ask you to open the folder using it. For additional details on connecting to remote containers, please see the [Open an existing folder in a container](https://code.visualstudio.com/docs/remote/containers#_quick-start-open-an-existing-folder-in-a-container) quickstart.

When you start the development container for the first time, the container will be built. This usually takes a few minutes.

## Next steps

* [Pre-deployment steps](./pre-deployment-steps.md)
