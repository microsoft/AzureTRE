# Dev environment

The supported development environments for Azure TRE are:

* [Native](#native-environment) and
* [Dev container](#dev-container)

## Prerequisites

Regardless of the development environment you choose, you will still need to fulfill the following prerequisites:

* [An Azure subscription](https://azure.microsoft.com/)
* [Azure Active Directory (AAD)](https://docs.microsoft.com/azure/active-directory/fundamentals/active-directory-whatis) with service principals created as explained in [Authentication & authorization](./auth.md)

### Obtain the source

Copy the source or clone the repository to your local machine or choose to use the pre-configured [dev container](#dev-container) via [GitHub Codespaces](https://github.com/features/codespaces).

![Clone options](../docs/assets/clone_options.png)

## Native environment

*Native* environment is the typical development environment based on your OS with the required tools installed on top. In addition to Unix shell (e.g., Bash or [Windows Subsystem for Linux (WSL)](https://docs.microsoft.com/en-us/windows/wsl/install-win10)) the following tools need to be installed:

* [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) >= 2.21.0
* [Azure Function Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local?tabs=windows%2Ccsharp%2Cbash#install-the-azure-functions-core-tools) - For [Resource Processor Function](../processor_function/README.md)
* [Docker](https://docs.docker.com/docker-for-windows/install/)
* IDE e.g., [Visual Studio Code](https://code.visualstudio.com/)
* [Porter](https://porter.sh/install/) - For workspace/workspace services development
* [Python](https://www.python.org/downloads/) >= 3.8 with [pip](https://packaging.python.org/tutorials/installing-packages/#ensure-you-can-run-pip-from-the-command-line)
* [Terraform](https://www.terraform.io/downloads.html) >= v0.15.3

The required Python packages can be installed with the following command in the root folder of the repository:

```cmd
pip install -r requirements.txt
```

## Dev container

<!-- markdownlint-disable-next-line MD013 -->
The files for a dev container that comes with the required tools installed is located in `/.devcontainer/` folder. Your native environment will require [Docker](https://docs.docker.com/docker-for-windows/install/) and IDE supporting development in containers such as [Visual Studio Code](https://code.visualstudio.com/). See [Developing inside a Container](https://code.visualstudio.com/docs/remote/containers) for instructions how to use the dev container with Visual Studio Code.

## (Optional) Install pre-commit hooks

Pre commit hooks help you lint your python code on each git commit, to avoid having to fail the build when submitting a PR. Installing pre-commit hooks is completely optional.

```cmd
pre-commit install
```
