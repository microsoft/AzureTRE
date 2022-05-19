param workspaceKeyVaultName string
param secretName string
@secure()
param secretValue string

resource localAdminPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  name: '${workspaceKeyVaultName}/${secretName}'
  properties: {
    value: secretValue
  }
}
