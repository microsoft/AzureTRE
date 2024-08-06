# Prerequisites

To deploy an Azure TRE instance, the following assets and tools are required:

* [Azure subscription](https://azure.microsoft.com)
* [Microsoft Entra ID](https://learn.microsoft.com/en-gb/entra/fundamentals/whatis) tenant in which you can create application registrations
* Git client such as [Git](https://git-scm.com/) or [GitHub Desktop](https://desktop.github.com/)
* [Docker Desktop](https://www.docker.com/products/docker-desktop)

## Development container

The Azure TRE solution contains a [development container](https://code.visualstudio.com/docs/remote/containers) with all the required tooling to develop and deploy the Azure TRE. To deploy an Azure TRE instance using the provided development container you will also need:

* [Visual Studio Code](https://code.visualstudio.com)
* [Remote containers extension for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

The files for the dev container are located in `/.devcontainer/` folder.

!!! tip
    An alternative of running the development container locally is to use [GitHub Codespaces](https://docs.github.com/en/codespaces).

!!! warning
    The procedures described throughout the documentation have been tested using machines with ***amd64 architecture*** CPUs. We have limited access to machines with other CPU architectures and issues may be encountered if those are used.

## Next steps

* [AzureTRE Deployment Repository](./deployment-repo.md)
