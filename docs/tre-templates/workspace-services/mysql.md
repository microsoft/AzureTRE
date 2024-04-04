# MySQL Workspace Service

See: [MySQL Azure](https://learn.microsoft.com/en-GB/azure/mysql/)

## Prerequisites

- [A base workspace deployed](../workspaces/base.md)

- The MySQL workspace service container image needs building and pushing:

  `make workspace_service_bundle BUNDLE=mysql`

## Authenticating to MySQL

1. Navigate to the MySQL workspace service using the `Mysql fqdn` from the details tab.
2. Using the Password found in Key Vault and the Username `mysqladmin`
3. Connect to the MySQL server on a VM with the following command shown below
   `mysql -h [fqdn] -u [username] -p [password]`

## Upgrading to version 1.0.0

Migrating existing MySQL services to the major version 1.0.0 is not currently supported. This is due to the breaking change in the Terraform to migrate from the deprecated mysql_server to the new mysql_flexible_server.