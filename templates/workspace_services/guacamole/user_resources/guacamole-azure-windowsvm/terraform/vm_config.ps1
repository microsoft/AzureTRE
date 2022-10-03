if( ${SharedStorageAccess} -eq 1 )
{
  $Command = "net use z: \\${StorageAccountName}.file.core.windows.net\${FileShareName} /u:AZURE\${StorageAccountName} ${StorageAccountKey}"
  $Command | Out-File  "C:\ProgramData\Start Menu\Programs\StartUp\attatch_storage.cmd" -encoding ascii
  Remove-Item -LiteralPath "C:\AzureData" -Force -Recurse
}

$PipConfigFolderPath = "C:\ProgramData\pip\"
If(!(Test-Path $PipConfigFolderPath))
{
  New-Item -ItemType Directory -Force -Path $PipConfigFolderPath
}

$PipConfigFilePath = $PipConfigFolderPath + "pip.ini"

$ConfigBody = @"
[global]
index = ${nexus_proxy_url}/repository/pypi/pypi
index-url = ${nexus_proxy_url}/repository/pypi/simple
trusted-host = ${nexus_proxy_url}
"@

# We need to write the ini file in UTF8 (No BOM) as pip won't understand Powershell's default encoding (unicode)
$Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
[System.IO.File]::WriteAllLines($PipConfigFilePath, $ConfigBody, $Utf8NoBomEncoding)

### Anaconda Config
if( ${CondaConfig} -eq 1 )
{
  conda config --add channels ${nexus_proxy_url}/repository/conda/  --system
  conda config --add channels ${nexus_proxy_url}/repository/conda-forge/  --system
  conda config --remove channels defaults --system
  conda config --set channel_alias ${nexus_proxy_url}/repository/conda/  --system
}

# Docker proxy config
$DaemonConfig = @"
{
"registry-mirrors": ["${nexus_proxy_url}:8083"]
}
"@
$DaemonConfig | Out-File -Encoding Ascii ( New-Item -Path $env:ProgramData\docker\config\daemon.json -Force )

# R config
$RconfigFilePathWindows = C:\Progra~1\R\R-4.2.1\etc\Rprofile.site
Add-Content $RconfigFilePathWindows "local({`n    r <- getOption(`"repos`")`n    r[`"Nexus`"] <- `"${NEXUS_PROXY_URL}/repository/r-proxy/`"`n    options(repos = r)`n})"
