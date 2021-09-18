# Dev environment

The supported development environments for Azure TRE are:

* [Dev container](#dev-container)

## Prerequisites

Regardless of the development environment you choose, you will still need to fulfill the following prerequisites:

* [An Azure subscription](https://azure.microsoft.com/)
* [Azure Active Directory (AAD)](https://docs.microsoft.com/azure/active-directory/fundamentals/active-directory-whatis) with service principals created as explained in [Authentication & authorization](../tre-admins/deploying-the-tre/auth.md)

### Obtain the source

Copy the source or clone the repository to your local machine or choose to use the pre-configured [dev container](#dev-container) via [GitHub Codespaces](https://github.com/features/codespaces).

![Clone options](../assets/clone_options.png)

## Dev container

<!-- markdownlint-disable-next-line MD013 -->
The files for a dev container that comes with the required tools installed is located in `/.devcontainer/` folder. Your native environment will require [Docker](https://docs.docker.com/docker-for-windows/install/) and IDE supporting development in containers such as [Visual Studio Code](https://code.visualstudio.com/). See [Developing inside a Container](https://code.visualstudio.com/docs/remote/containers) for instructions how to use the dev container with Visual Studio Code.

## (Optional) Install pre-commit hooks

Pre commit hooks help you lint your python code on each git commit, to avoid having to fail the build when submitting a PR. Installing pre-commit hooks is completely optional.

```cmd
pre-commit install
```
