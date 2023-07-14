# Azure Machine Learning Service bundle

See: [https://azure.microsoft.com/services/machine-learning/](https://azure.microsoft.com/services/machine-learning/)

This service installs the following resources into an existing virtual network within the workspace:

![Azure Machine Learning Service](images/aml_service.png)

When deploying the service the Azure ML workspace can be exposed publicly or access restricted to the virtual network. Depending on the choice appropriate network security rules are added. This also means that in the public configuration compute instances can be deployed with public IPs, and in the private configuration they must be deployed with no public IP.

Any users with the role of `Workspace Researcher` will be assigned the `AzureML Data Scientist` role within the AML workspace.

To ensure AML compute instances are deployed with the appropriate configuration we suggest they are deployed using an Compute Instance User Resource.

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
