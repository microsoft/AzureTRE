if( ${SharedStorageAccess} -eq 1 )
{
  $password = ConvertTo-SecureString -String ${StorageAccountKey} -AsPlainText -Force
  $credential = New-Object System.Management.Automation.PSCredential -ArgumentList "AZURE\${StorageAccountName}", $password
  New-PSDrive -Name Z -PSProvider FileSystem -Root "\\${StorageAccountName}.file.core.windows.net\${FileShareName}" -Credential $credential -Persist -Scope Global
  cmdkey /add:${StorageAccountName}.file.core.windows.net /user:Azure\${StorageAccountName} /pass:${StorageAccountKey}
}
