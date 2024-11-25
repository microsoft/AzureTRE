# Enabling Customer-managed keys for TRE resources

You can enable customer-managed keys (CMK) for supporting resources in Azure TRE.

!!! warning
    Currently Azure TRE only supports CMK encryption for resources in the TRE core.  
    CMK encryption is not supported for the rest of the resources such as those deployed by a TRE workspace.


When enabled, CMK encryption provides an additional layer of encryption control for supported Azure resources within the TRE by allowing you to manage and control the encryption keys used to protect your data.

To enable CMK encryption, set `enable_cmk_encryption: true` in the developer settings section of your `config.yaml` file.

For more information about CMKs, see [Use customer-managed keys with Azure Storage encryption](https://learn.microsoft.com/azure/storage/common/customer-managed-keys-overview).

## Key Vault configuration
The CMKs for Azure TRE can be stored in either a Key Vault deployed by TRE itself, or in an external Key Vault provided by the user.  

To have TRE create and manage its own Key Vault for storing CMKs, specify the `ENCRYPTION_KV_NAME` parameter in the `config.yaml` file.  

Alternatively, to use your own existing Key Vault, provide the `EXTERNAL_KEY_STORE_ID` parameter pointing to your Key Vault resource ID.
