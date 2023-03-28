# Supported Clouds

AzureTRE can be installed on the following clouds:
1. Azure Public cloud
2. [Azure US Government Cloud](https://azure.microsoft.com/en-us/explore/global-infrastructure/government/)

## Supported Services

1. Azure Public cloud - All services are supported.
1. In Azure US Government Cloud the following services are supported
    - All type of workspaces
    - Virtual Desktops service - Guacamole
    - Linux and Windows VM machines

## Technical Notes

When Using Azure US Government Cloud make sure to:
1. Setup the cloud in Azure CLI - `az cloud set --name AzureUSGovernment`
1. Setup the AZURE_ENVIRONMENT param in CI/CD pipelines to `AzureUSGovernment` - as mentioned in [CI/CD predeployment steps](setup-instructions/cicd-pre-deployment-steps.md)
