# MLflow Workspace Service

See: <https://www.mlflow.org>

## Prerequisites

- [A base workspace deployed](../workspaces/base.md)

- The MLflow workspace service container image needs building and pushing:

  `make build-and-push-mlflow`

## MLflow Workspace VM Configuration

Each MLflow server deployment creates a PowerShell (for Windows) and a shell script (for Linux) with the same name as the MLflow server, in the shared storage mounted on the researcher VMs. These scripts will configure the researcher VMs (by installing the required packages and setting up the environment variables) to communicate with the MLflow tracking server.

!!! note
    Please ensure that [nexus reposiory](https://microsoft.github.io/AzureTRE/tre-admins/setup-instructions/configuring-shared-services/) is configured before running the above scripts.

## MLflow set tracking URI

Researchers will be required to set the remote tracking URI in their scripts

```python
remote_server_uri = "https://xxxxxxx.azurewebsites.net/"

mlflow.set_tracking_uri(remote_server_uri)
```
