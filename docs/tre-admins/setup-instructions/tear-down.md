# Tear-down

To remove the Azure TRE and its resources from your Azure subscription run:

```cmd
make tre-destroy
```

Alternatively, you can delete the resource groups in Azure Portal or using the CLI:

```cmd
az group delete --name <resource group name>
```

Finally, delete the app registrations in Azure Portal or using the CLI:

```cmd
az ad app delete --id <application client ID>
```
