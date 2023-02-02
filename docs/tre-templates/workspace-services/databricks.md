# Azure Databricks workspace service bundle

See: [https://azure.microsoft.com/en-us/products/databricks/](https://azure.microsoft.com/en-us/products/databricks/)

This service installs the following resources into an existing virtual network within the workspace:

![Azure Databricks workspace service](../../assets/databricks_workspace_service.png)


## Properties

- `is_exposed_externally` - If `True`, the Azure Databricks workspace is accessible from outside of the worksapce virtual network. If `False` use a Guacamole VM and the `internal_connection_uri` to access Databricks workspace.


## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
