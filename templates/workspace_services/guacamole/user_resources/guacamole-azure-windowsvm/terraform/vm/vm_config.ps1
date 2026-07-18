Remove-Item -LiteralPath "C:\AzureData" -Force -Recurse
$ErrorActionPreference = "Stop"

if( ${SharedStorageAccess} -eq 1 )
{
  $Command = "net use z: \\${StorageAccountFileHost}\${FileShareName} /u:AZURE\${StorageAccountName} ${StorageAccountKey}"
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
$RConfig = @"
local({
    r <- getOption("repos")
    r["Nexus"] <- "${nexus_proxy_url}/repository/r-proxy/"
    options(repos = r)
})
"@

$RBasePath = "$Env:ProgramFiles\R"

if (Test-Path $RBasePath) {
  $RVersions = Get-ChildItem -Path $RBasePath -Directory | Where-Object { $_.Name -like "R-*" }

  foreach ($RVersion in $RVersions) {
      $ConfigPath = Join-Path -Path $RVersion.FullName -ChildPath "etc\Rprofile.site"
      $RConfig | Out-File -Encoding Ascii (New-Item -Path $ConfigPath -Force)
  }
}


# Pinned versions - update these to roll the installed tooling forward.
$AzureCliVersion       = "2.81.0"
$StorageExplorerVersion = "1.37.0"

$ToolsDir = Join-Path $env:TEMP "tre-tools"
New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null

# Speeds up Invoke-WebRequest considerably by not rendering a progress bar
$ProgressPreference = "SilentlyContinue"

function Wait-ForNexus {
  param(
    [string]$Url = "${nexus_proxy_url}",
    [int]$TimeoutSeconds = 600,
    [int]$IntervalSeconds = 15
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      Invoke-WebRequest -Uri $Url -Method Head -UseBasicParsing -TimeoutSec 30 | Out-Null
      Write-Host "Nexus proxy is reachable at $Url"
      return $true
    }
    catch {
      Write-Host "Waiting for Nexus proxy at $Url - $($_.Exception.Message)"
      Start-Sleep -Seconds $IntervalSeconds
    }
  }

  Write-Host "WARNING: Nexus proxy at $Url was not reachable within $TimeoutSeconds seconds"
  return $false
}

function Install-TreTool {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$OutFile,
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$ArgumentList,
    [int]$MaxAttempts = 5
  )

  # Skip installs on failure rather than aborting the whole VM configuration.
  try {
    Write-Host "Downloading $Name from $Url"
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
      try {
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
        break
      }
      catch {
        if ($attempt -eq $MaxAttempts) { throw }
        Write-Host "Download of $Name failed (attempt $attempt/$MaxAttempts), retrying - $($_.Exception.Message)"
        Start-Sleep -Seconds 15
      }
    }
    Write-Host "Installing $Name"
    $process = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) {
      Write-Host "WARNING: $Name installer exited with code $($process.ExitCode)"
    }
  }
  catch {
    Write-Host "WARNING: Failed to install $Name - $($_.Exception.Message)"
  }
}

# Make sure the proxy is up before pulling any of the installers below.
Wait-ForNexus | Out-Null

$AzureCliMsi = Join-Path $ToolsDir "azure-cli.msi"
Install-TreTool -Name "Azure CLI" `
  -Url "${nexus_proxy_url}/repository/azure-cli/azure-cli-$AzureCliVersion-x64.msi" `
  -OutFile $AzureCliMsi `
  -FilePath "msiexec.exe" `
  -ArgumentList @("/i", "`"$AzureCliMsi`"", "/qn", "/norestart")

$env:Path = "$Env:ProgramFiles\Microsoft SDKs\Azure\CLI2\wbin;$Env:ProgramFiles (x86)\Microsoft SDKs\Azure\CLI2\wbin;$env:Path"

$VsCodeSetup = Join-Path $ToolsDir "vscode-setup.exe"
Install-TreTool -Name "Visual Studio Code" `
  -Url "${nexus_proxy_url}/repository/vscode/latest/win32-x64/stable" `
  -OutFile $VsCodeSetup `
  -FilePath $VsCodeSetup `
  -ArgumentList @("/VERYSILENT", "/NORESTART", "/MERGETASKS=!runcode,addcontextmenufiles,addcontextmenufolders,addtopath")

# Azure Storage Explorer - proxied via the Nexus storage-explorer raw repository
$StorageExplorerSetup = Join-Path $ToolsDir "storage-explorer.exe"
Install-TreTool -Name "Azure Storage Explorer" `
  -Url "${nexus_proxy_url}/repository/storage-explorer/v$StorageExplorerVersion/StorageExplorer-windows-x64.exe" `
  -OutFile $StorageExplorerSetup `
  -FilePath $StorageExplorerSetup `
  -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/ALLUSERS")
