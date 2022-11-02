# Setup Auth configuration

Next, you will set the configuration variables for the specific Azure TRE instance:

1. Open the `/templates/core/.env.sample` file and then save it without the .sample extension. You should now have a file called `.env` located in the `/templates/core` folder.
1. Decide on a name for your `TRE_ID`, which is an alphanumeric (with underscores and hyphens allowed) ID for the Azure TRE instance. The value will be used in various Azure resources and AAD application names. It **needs to be globally unique and less than 12 characters in length**. Use only lowercase letters. Choose wisely!
1. Once you have decided on which AD Tenant paradigm, then you should be able to set `AAD_TENANT_ID`
1. Your AAD Tenant Admin can now use the terminal window in Visual Studio Code to execute the following script from within the development container to create all the AAD Applications that are used for TRE. The details of the script are covered in the [auth document](../auth.md).

   ```bash
   make auth
   ```
  !!! note
      A new auth.env file will be created under /devops folder. It will contain all the credentials created by the `make auth` command.

  !!! note
      In case you have several subscriptions and would like to change your default subscription use `az account set --subscription <desired subscription ID>`

  !!! note
      The full functionality of the script requires directory admin privileges. You may need to contact your friendly Azure Active Directory admin to complete this step. The app registrations can be created manually in Azure Portal too. For more information, see [Authentication and authorization](../auth.md).
  

All other variables can have their default values for now.

## Add admin user

Make sure the **TRE Administrators** and **TRE Users** roles, defined by the API app registration, are assigned to your user and others as required. See [Enabling users](../auth.md#enabling-users) for instructions.
