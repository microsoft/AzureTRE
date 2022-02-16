if( ${SharedStorageAccess} -eq 1 )
{
  $password = ConvertTo-SecureString -String ${StorageAccountKey} -AsPlainText -Force
  $credential = New-Object System.Management.Automation.PSCredential -ArgumentList "AZURE\${StorageAccountName}", $password
  New-PSDrive -Name Z -PSProvider FileSystem -Root "\\${StorageAccountName}.file.core.windows.net\${FileShareName}" -Credential $credential -Persist -Scope Global
  $command = "powershell -WindowStyle hidden ""cmdkey /add:${StorageAccountName}.file.core.windows.net /user:Azure\${StorageAccountName} /pass:${StorageAccountKey}"""
  $command | Out-File "C:\Users\${AdminUser}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\AddCredentials.cmd"
}
