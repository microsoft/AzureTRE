# Deployment quickstart

By following this quickstart you will deploy an Azure TRE instance for training and evaluation purposes using the minimum amount of steps and actions.

## Prerequisites

To deploy an Azure TRE instance, there are a couple of prerequisites:

* [Azure subscription](https://azure.microsoft.com)
* Azure Active Directory tenant in which you can create application registrations.
* [Git](https://git-scm.com/) or [GitHub Desktop](https://desktop.github.com/)

The Azure TRE solution contains a [development container](https://code.visualstudio.com/docs/remote/containers) with all the required tooling to develop and deploy the Azure TRE. To deploy an Azure TRE instance using the provided development container you will also need:

* [Docker desktop](https://www.docker.com/products/docker-desktop)
* [Visual Studio Code](https://code.visualstudio.com)
* [Remote containers extension for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

## Clone the Azure TRE Git repository

Clone the Azure TRE Git repository on GitHub to your local computer.

```bash
> git clone https://github.com/microsoft/AzureTRE.git
```

The Git repository will host some basic configuration for the TRE instances that are deployed from a given repository. Create a new branch for the instance that you are about to deploy.

```bash
> cd AzureTRE
AzureTRE> git checkout -b quickstartenv
```

Now, let's open the cloned repository in Visual Studio Code and connect to the development container.

```bash
AzureTRE> code .
```

> Visual Studio Code should recognize the available development container. For additional details on connecting to remote containers, please see the [Open an existing folder in a container](https://code.visualstudio.com/docs/remote/containers#_quick-start-open-an-existing-folder-in-a-container) quickstart.

