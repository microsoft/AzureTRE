Remove-Item -LiteralPath "C:\AzureData" -Force -Recurse
$ErrorActionPreference = "Stop"

if( ${SharedStorageAccess} -eq 1 -And ${StorageAccountKey1} -match "/")
{
  $Command = "net use z: \\${StorageAccountFileHost}\${FileShareName} /u:AZURE\${StorageAccountName} ${StorageAccountKey2}"
  $Command | Out-File  "C:\ProgramData\Start Menu\Programs\StartUp\attach_storage.cmd" -encoding ascii
} else
{
  $Command = "net use z: \\${StorageAccountFileHost}\${FileShareName} /u:AZURE\${StorageAccountName} ${StorageAccountKey1}"
  $Command | Out-File  "C:\ProgramData\Start Menu\Programs\StartUp\attach_storage.cmd" -encoding ascii
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
  conda config --add channels ${nexus_proxy_url}/repository/conda-mirror/main/  --system
  conda config --add channels ${nexus_proxy_url}/repository/conda-repo/main/  --system
  conda config --remove channels defaults --system
  conda config --set channel_alias ${nexus_proxy_url}/repository/conda-mirror/  --system
}

# Docker proxy config
$DaemonConfig = @"
{
"registry-mirrors": ["${nexus_proxy_url}:8083"]
}
"@
$DaemonConfig | Out-File -Encoding Ascii ( New-Item -Path $env:ProgramData\docker\config\daemon.json -Force )

# R config
# $RconfigFilePathWindows = C:\Progra~1\R\4.1.2\etc\Rprofile.site
#Add-Content $RconfigFilePathWindows "local({`n    r <- getOption(`"repos`")`n    r[`"Nexus`"] <- `"${nexus_proxy_url}/repository/r-proxy/`"`n    options(repos = r)`n})"
# echo "local({`n    r <- getOption(`"repos`")`n    r[`"Nexus`"] <- `"${nexus_proxy_url}/repository/r-proxy/`"`n    options(repos = r)`n})" > $RconfigFilePathWindows
$RConfig = @"
local({
    r <- getOption("repos")
    r["Nexus"] <- "${nexus_proxy_url}/repository/r-proxy/"
    options(repos = r)
})
"@
$RConfig | Out-File -Encoding Ascii ( New-Item -Path $Env:ProgramFiles\R\R-4.1.2\etc\Rprofile.site -Force )

