# InnerEye DeepLearning Service Bundle

- [Azure ML](../../../templates/workspace_services/azureml)

See: [https://github.com/microsoft/InnerEye-DeepLearning](https://github.com/microsoft/InnerEye-DeepLearning)

## Firewall Rules

Please be aware that the following Firewall rules are opened for the workspace when this service is deployed. These are all dependencies needed by InnerEye to be able to develop and train models:

URLs:

- *.anaconda.com
- *.anaconda.org
- binstar-cio-packages-prod.s3.amazonaws.com
- *pythonhosted.org
- github-cloud.githubusercontent.com
- azure.archive.ubuntu.com (git lfs package)
- packagecloud.io (git lfs package installation script)

## Initial setup

Provision an InnerEye workspace by invoking a POST to ```https://<treid>.<region>.cloudapp.azure.com/api/workspaces``` with the following payload:

```json
    {
    "templateName": "tre-workspace-innereye",
            "properties": {
                "display_name": "InnerEye",
                "description": "InnerEyer workspace",
                "client_id": "<WORKSPACE_API_CLIENT_ID>",
                "inference_sp_client_id": "<spn_client_id>",
                "inference_sp_client_secret": "<spn_client_secret>"
            }
    }
```

This will provision Base Workspace, with AML service and InnerEye service, including InnerEye Inference web app.

## Running the InnerEye HelloWorld

### Preparation steps performed by the TRE Admin

1. Ensure that you have completed ["Configuring Shared Services"](../../tre-admins/setup-instructions/configuring-shared-services.md)
1. Log onto a TREAdmin Jumpbox and mirror Github repos needed by InnerEye Helloworld:

    ```cmd
    ./templates/workspace_services/gitea/gitea_migrate_repo.sh -t <tre_id> -g https://github.com/microsoft/InnerEye-DeepLearning
    ./templates/workspace_services/gitea/gitea_migrate_repo.sh -t <tre_id> -g https://github.com/analysiscenter/radio
    ./templates/workspace_services/gitea/gitea_migrate_repo.sh -t <tre_id> -g https://github.com/microsoft/InnerEye-Inference
    ```

### Setup the InnerEye run from AML Compute Instance

1. Log onto a VM in the workspace
1. In the VM open your browser and navigate to [ml.azure.com](https://ml.azure.com), login, select the right Subscription and AML workspace.
1. Select the Notebooks tab and then click Terminal. This will open a terminal on a running compute instance
1. Pull the InnerEye-DeepLearning git repo from Gitea mirror and configure:

    ```cmd
    git clone https://gitea-<TRE_ID>.azurewebsites.net/giteaadmin/InnerEye-DeepLearning
    cd InnerEye-DeepLearning
    curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
    sudo apt-get install git-lfs
    git lfs install
    git lfs pull
    export PIP_INDEX_URL=https://nexus-<TRE_ID>.azurewebsites.net/repository/apt-pypi/simple
    conda init
    conda env create --file environment.yml
    conda activate InnerEye
    ```

1. Login to AzureCLI and set default subscription if needed

    ```cmd
    az login
    az account set --subscription 
    ```

1. Create a "datasets" container

    ```az storage container create --name datasets --account-name stgws<workspace_id>```
1. Copy `dataset.csv` file from `Tests/ML/test_data/dataset.csv` to the `hello_world` folder:

    ```az storage blob upload --account-name stgws<workspace_id> --container-name datasets --file ./Tests/ML/test_data/dataset.csv --name hello_world/dataset.csv```
1. Copy the whole `train_and_test_data` folder from `Test/ML/test_data/train_and_test_data` to the `hello_world` folder:

    ```az storage blob directory upload -c datasets --account-name stgws<workspace_id> -s "./Tests/ML/test_data/train_and_test_data" -d hello_world --recursive```

1. Get storage keys for your storage:

    ```az storage account keys list --account-name stgws<workspace_id>```

1. Update the following variables in `InnerEye/settings.yml`: subscription_id, resource_group, workspace_name, cluster (see [AML setup](https://github.com/microsoft/InnerEye-DeepLearning/blob/main/docs/setting_up_aml.md) for more details).
1. Navigate to `Data stores` in AML Workspace. Create a New datastore named `innereyedatasets` and link it to your storage account and datasets container. Use the key collected from the step above.
1. Back from the Terminal run

   ```cmd
   python InnerEye/ML/runner.py --model=HelloWorld --azureml=True
   ```

1. The runner will provide you with a link and ask you to open it to login. Copy the link and open it in browser (Edge) on the DSVM and login. The run will continue after login.
1. In your browser navigate to [https://ml.azure.com](https://ml.azure.com) and open the `Experiments` tab to follow the progress of the training

## Configuring and testing inference service

The workspace service provisions an App Service Plan and an App Service for hosting the inference webapp. The webapp will be integrated into the workspace network, allowing the webapp to connect to the AML workspace. Following the setup you will need to:

1. Log onto a VM in the workspace and run:

    ```cmd
    git clone https://gitea-<TRE_ID>.azurewebsites.net/giteaadmin/InnerEye-Inference
    cd InnerEye-Inference
    ```

1. Create a file named "set_environment.sh" with the following variables as content:

    ```bash
    #!/bin/bash
    export CUSTOMCONNSTR_AZUREML_SERVICE_PRINCIPAL_SECRET=<inference_sp_client_secret-from-above>
    export CUSTOMCONNSTR_API_AUTH_SECRET=<generate-a-random-guid--that-is-used-for-authentication>
    export CLUSTER=<name-of-compute-cluster>
    export WORKSPACE_NAME=<name-of-AML-workspace>
    export EXPERIMENT_NAME=<name-of-AML-experiment>
    export RESOURCE_GROUP=<name-of-resource-group>
    export SUBSCRIPTION_ID=<subscription-id>
    export APPLICATION_ID=<inference_sp_client_id-from-above>
    export TENANT_ID=<tenant-id>
    export DATASTORE_NAME=inferencedatastore
    export IMAGE_DATA_FOLDER=imagedata
    ```

1. Upload the configuration file to the web app:

    ```cmd
    az webapp up --name <inference-app-name> -g <resource-group-name>
    ```

1. Create a new container in your storage account for storing inference images called `inferencedatastore`.
1. Create a new folder in that container called `imagedata`.
1. Navigate to the ml.azure.com, `Datastores` and create a new datastore named `inferencedatastore` and connect it to the newly created container.
1. Test the service by sending a GET or POST command using curl or Invoke-WebRequest where API_AUTH_SECRET is the random GUID generated for CUSTOMCONNSTR_API_AUTH_SECRET above:

   Simple ping:

    ```cmd
    Invoke-WebRequest https://yourservicename.azurewebsites.net/v1/ping -Headers @{'Accept' = 'application/json'; 'API_AUTH_SECRET' = 'your-secret-1234-1123445'}
    ```

    Test connection with AML:

    ```cmd
    Invoke-WebRequest https://yourservicename.azurewebsites.net/v1/model/start/HelloWorld:1 -Method POST -Headers @{'Accept' = 'application/json'; 'API_AUTH_SECRET' = 'your-secret-1234-1123445'}
    ```
