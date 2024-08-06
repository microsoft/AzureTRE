# MLflow Workspace Service

See: <https://www.mlflow.org>

## Prerequisites

- [A base workspace deployed](https://microsoft.github.io/AzureTRE/tre-templates/workspaces/base/)

## MLflow Workspace VM Configuration

Each MLflow server deployment creates a PowerShell (for Windows) and a shell script (for Linux) with the same name as the MLflow server, in the shared storage mounted on the researcher VMs.
These scripts will configure the researcher VMs (by installing the required packages and setting up the environment variables) to communicate with the MLflow tracking server.

!!! note
    Please ensure that [nexus reposiory](https://microsoft.github.io/AzureTRE/tre-admins/setup-instructions/configuring-shared-services/) is configured before running the above scripts.

## MLflow set tracking URI

Researchers will be required to set the remote tracking URI in their scripts

```python
remote_server_uri = "https://xxxxxxx.azurewebsites.net/"

mlflow.set_tracking_uri(remote_server_uri)
```

## Using with Conda-Forge

If working with Conda-Forge you need to ensure the user resource you are using is configured correctly and using the channels available via the [Nexus repository](../shared-services/nexus/).
If the user resource you have deployed used one of the pre-existing Guacamole user resource templates and has conda installed by default, conda will already be configured to use the correct channels via Nexus.
If not and conda has been manually deployed on the user resource, the following script can be used to configure conda:

```shell
  conda config --add channels ${nexus_proxy_url}/repository/conda/  --system
  conda config --add channels ${nexus_proxy_url}/repository/conda-forge/  --system
  conda config --remove channels defaults --system
  conda config --set channel_alias ${nexus_proxy_url}/repository/conda/  --system
```

### conda.yml

When using a `conda.yml` file to configure your MLFlow environment it is required to specify the channels to use.  
As the traditional channels (conda-forge, defaults etc) have been replaced with Nexus channels, you must ensure that the Nexus channels are being specified here instead.
To retireve these channels, run `conda config --show channels` once conda has been configured to use Nexus.

!!! note
  When logging models using sklearn, an optional parameter `conda_env` can be passed as either JSON or YML.  If this is not passed a default `conda.yml` will be generate for the model, targeting the channel `conda-forge` causing any subsequent environments created using the model to fail.
  See the official documentation [here](https://www.mlflow.org/docs/latest/python_api/mlflow.sklearn.html) for the full details.
