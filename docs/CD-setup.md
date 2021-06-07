# Continuous delivery with GitHub Actions

## Setup

Create an SPN that will be used to provision resources in your Azure subscription:

```cmd
az account set -s {SubID}
az ad sp create-for-rbac -n "MyTREAppDeployment" --role Owner --scopes /subscriptions/{SubID} --sdk-auth
```
Save JSON the output in a GitHub secret called `AZURE_CREDENTIALS`. 

You will also need to create the following secrets:

- `TRE_ID`
- `ACR_NAME`
- `MGMT_RESOURCE_GROUP`
- `STATE_STORAGE_ACCOUNT_NAME`

The `Deploy TRE` workflow can then be run.