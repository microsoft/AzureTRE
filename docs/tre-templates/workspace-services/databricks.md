# Azure Databricks workspace service bundle

See: [https://azure.microsoft.com/en-us/products/databricks/](https://azure.microsoft.com/en-us/products/databricks/)

This service along with Azure Databricks Private Authentication Shared Service installs the following resources into an existing virtual network within the workspace:

![Azure Databricks workspace service](../../assets/databricks_workspace_service.png)


## Properties

- `is_exposed_externally` - If `True`, the Azure Databricks workspace is accessible from outside of the workspace virtual network. If `False` use a Guacamole VM and copy the `connection_uri` to access Databricks workspace.


## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
- An Azure Databricks Private Authentication Shared Service deployed - required for authenticating to an Azure Databricks workspace.


## References

- Databricks workspace service and authentication shared service deployed according to simplified deployment, for more information see: [Enable Azure Private Link as a simplified deployment](https://learn.microsoft.com/en-us/azure/databricks/administration-guide/cloud-configurations/azure/private-link-simplified)
