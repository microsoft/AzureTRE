# OHDSI Workspace Service

### IMPORTANT
- This workspace service does not work "out of the box". It requires additional networking configuration to work properly. See the [Networking configuration](#networking-configuration) section for more details.
- Currently the only data source supported by the workspace service is Azure Synapse.

# Networking configuration
Deploying the OHDSI workspace is not enough for it to function properly, in order for it to work properly, the following networking configuration should be in place:

### 1. The resource processor should be able to access the data source
Multiple OHDSI workspace services cannot share the same schemas because each OHDSI instance is changing the schemas, which could potentially cause conflicts. To avoid this, every workspace service must work on its own schemas. To do this, we use golden copying. This means that the "main" schemas remain untouched, and every workspace service has its own copy of it, which it can modify.

Since the resource processor is in charge of duplicating the schemas, the data source has to be accessible from the resource processor's VNet in order to be able to create them.


### 2. The workspace should be able to access the data source
In order to access the CDM from ATLAS, the data source should be accessible from the workspace's VNet.
