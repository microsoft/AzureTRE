# Azure Machine Learning Service bundle

See: [https://azure.microsoft.com/services/machine-learning/](https://azure.microsoft.com/services/machine-learning/)

This service installs the following resources into an existing virtual network within the workspace:

![Azure Machine Learning Service](images/aml_service.png)

## Properties

- `display_name` - The name of the Azure Machine Learning workspace.
- `description` - The description of the Azure Machine Learning workspace.
- `is_exposed_externally` - If `True`, the Azure Machine Learning workspace is accessible from outside of the worksapce virtual network.


## Firewall Rules

Please be aware that the following outbound Firewall rules are opened for the workspace when this service is deployed, including to Azure Storage. This does open the possibility to extract data from a workspace if the user is determined to do so. Work is ongoing to remove some of these requirements:

Service Tags:
- AzureActiveDirectory
- AzureResourceManager
- AzureMachineLearning"
- Storage.`{AzureRegion}`
- MicrosoftContainerRegistry

URLs:
- aadcdn.msftauth.net
- ml.azure.com


## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
