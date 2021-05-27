# Continous delivery with GitHub Actions

## Setup

Create an SPN that will be used to provision resource in your Azure subscription:

```cmd
az account set -s {SubID}
az ad sp create-for-rbac -n "MyTREAppDeployment" --role Contributor --scopes /subscriptions/{SubID} --sdk-auth
```

The output includes credentials that you must protect. Create a create a new Actions seceret in your GitHub repository and paste the JSON output.

You can now reference the seceret in your GitHub actions by setting the environment (e.g. `environment: Dev`) and then retrieving the secert: `creds: ${{ secrets.AZURE_CREDENTIALS }}`
