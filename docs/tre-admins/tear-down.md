# Tear-down

To remove the Azure TRE and its resources from your Azure subscription run:

```cmd
make tre-destroy
```

Alternatively, you can directly delete the resource groups in Azure Portal or using the CLI, however the `make` method is recommended if you plan to re-deploy the Azure TRE since it performs [additional tidy up](https://github.com/microsoft/AzureTRE/blob/main/devops/scripts/destroy_env_no_terraform.sh) which prevent re-deployment errors.

```cmd
az group delete --name <resource group name>
```

Finally, delete the app registrations in Azure Portal or using the CLI:

```cmd
az ad app delete --id <application client ID>
```
