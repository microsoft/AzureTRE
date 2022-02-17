if( ${SharedStorageAccess} -eq 1 )
{
  $Command = "net use z: \\${StorageAccountName}.file.core.windows.net\${FileShareName} /u:AZURE\${StorageAccountName} ${StorageAccountKey}"
  $Command | Out-File  "C:\ProgramData\Start Menu\Programs\StartUp\attatch_storage.cmd" -encoding ascii
  Remove-Item -LiteralPath "C:\AzureData" -Force -Recurse
}
