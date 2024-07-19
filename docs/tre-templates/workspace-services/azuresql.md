# Azure SQL Workspace Service

See: [Azure SQL Database](https://learn.microsoft.com/en-us/azure/azure-sql/database)

## Prerequisites

- The base workspace deployed, or a workspace derived from the base workspace

- The Azure SQL workspace service container image published to your TRE:

  `make workspace_service_bundle BUNDLE=azuresql`

- Guacamole, with a VM containing SQL Server Management Studio or Azure Data Studio in order to connect - the Azure Data Science VM template contains both of these


## Authentication

- Server name:  Shown on the details page of the service in the Azure TRE portal under **Azure SQL FQDN**
- Authentication method: **SQL Server Authentication**
- Administrator credentials:
  - Username:  **azuresqladmin**
  - Password:  *(available in the workspace keyvault)*

## Supported SKUs

The following Azure SQL SKUs have been added to the template:

| Service Tier | Level | DTUs     |
|--------------|-------|----------|
| Standard     | S1    | 20 DTUs  |
| Standard     | S2    | 50 DTUs  |
| Standard     | S3    | 100 DTUs |
| Standard     | S4    | 200 DTUs |
| Standard     | S6    | 400 DTUs |

For costs please [Azure SQL Database pricing](https://azure.microsoft.com/en-us/pricing/details/azure-sql-database/single/) and select **DTU** as the purchase model.

### Adding new SKUs

To add new SKU options within the template, please determine the SKU names using:

```bash
az sql db list-editions --location <AZURE_REGION> --output table
```

Then add the SKUs in the following places:

1. In the `templates/workspace_services/azuresql/template_schema.yaml` file under `properties.sql_sku.enum`.
2. In the `templates/workspace_services/azuresql/terraform/locals.tf` file under `azuresql_sku`.
3. Above in this document.

Once added, increment the version number in the `templates/workspace_services/azuresql/porter.yaml` file, and republish the template with the following command:

  `make workspace_service_bundle BUNDLE=azuresql`
