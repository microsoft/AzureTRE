# InnerEye DeepLearning Service Bundle

See: [https://github.com/microsoft/InnerEye-DeepLearning](https://github.com/microsoft/InnerEye-DeepLearning)

## Firewall Rules

Please be aware that the following Firewall rules are opened for the workspace when this service is deployed:

URLs:

- *.anaconda.com
- *.anaconda.org
- binstar-cio-packages-prod.s3.amazonaws.com
- github.com
- *pypi.org
- *pythonhosted.org
- github-cloud.githubusercontent.com

## Manual Deployment

1. Prerequisites for deployment:
    - [A workspace with an Azure ML Service bundle installed](../azureml)

1. Create a copy of `workspaces/services/innereye_deeplearning/.env.sample` with the name `.env` and update the variables with the appropriate values.

1. Build and install the InnerEye Deep Learning Service bundle
    - `make porter-build DIR=./workspaces/services/innereye_deeplearning`  
    - `make porter-install DIR=./workspaces/services/innereye_deeplearning`

## Running the InnerEye HelloWorld on AML Compute Cluster

1. Log onto a VM in the workspace, open PowerShell and run:

- ```git clone https://github.com/microsoft/InnerEye-DeepLearning```
- ```cd InnerEye-DeepLearning```
- ```git lfs install```
- ```git lfs pull```
- ```conda init```
- ```conda env create --file environment.yml```
- Restart PowerShell and navigate to the "InnerEye-DeepLearning" folder
- ```conda activate InnerEye```
- Open Azure Storage Explorer and connect to your Storage Account using name and access key
- On the storage account create a container with name ```datasets``` and a folder named ```hello_world```
- Copy ```dataset.csv``` file from Tests/ML/test_data/dataset.csv to the "hello_world" folder
- Copy the whole ```train_and_test_data``` folder from Test/ML/test_data/train_and_test_data to the "hello_world" folder
- Update the following variables in ```InnerEye/settings.yml```: subscription_id, resource_group, workspace_name, cluster (see [AML setup](https://github.com/microsoft/InnerEye-DeepLearning/blob/main/docs/setting_up_aml.md) for more details).
- Open your browser to ml.azure.com, login, select the right Subscription and AML workspace and then navigate to "Datastores". Create a New datastore named "innereyedatasets" and link it to your storage account and datasets container.
- Back from PowerShell run ```python InnerEye/ML/runner.py --model=HelloWorld --azureml=True```
- The runner will provide you with a link and ask you to open it to login. Copy the link and open it in browser (Edge) on the DSVM and login. The run will continue after login.
- In your browser navigate to ml.azure.com and open the "Experiments" tab to follow the progress of the training
