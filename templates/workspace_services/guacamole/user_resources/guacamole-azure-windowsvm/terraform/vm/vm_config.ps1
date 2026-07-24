$ErrorActionPreference = "Stop"
Remove-Item -LiteralPath "C:\AzureData" -Force -Recurse -ErrorAction SilentlyContinue

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

$NexusHost = ([System.Uri]"${nexus_proxy_url}").Host

$ConfigBody = @"
[global]
index = ${nexus_proxy_url}/repository/pypi/pypi
index-url = ${nexus_proxy_url}/repository/pypi/simple
trusted-host = $NexusHost
"@

# We need to write the ini file in UTF8 (No BOM) as pip won't understand Powershell's default encoding (unicode)
$Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
[System.IO.File]::WriteAllLines($PipConfigFilePath, $ConfigBody, $Utf8NoBomEncoding)

# Docker proxy config (best-effort — only applies if Docker is pre-installed)
try {
  $dockerConfigDir = "$env:ProgramData\docker\config"
  if (!(Test-Path $dockerConfigDir)) {
    New-Item -ItemType Directory -Force -Path $dockerConfigDir | Out-Null
  }
  $DaemonConfig = @"
{
"registry-mirrors": ["${nexus_proxy_url}:8083"]
}
"@
  $DaemonConfig | Out-File -Encoding Ascii "$dockerConfigDir\daemon.json"
} catch {
  Write-Host "Skipping Docker proxy config: $_"
}

# Pinned versions - update these to roll the installed tooling forward.
$AzureCliVersion        = "2.88.0"
$VsCodeVersion          = "1.129.1"
$StorageExplorerVersion = "1.44.0"
$MiniforgeVersion       = "26.3.2-3"
$JupyterLabVersion      = "4.6.2"
$RVersion               = "4.6.1"
$RStudioVersion         = "2026.07.1-147"
$GitVersion             = "2.55.0"
$MiniforgePath          = "C:\Miniforge3"
$InstallAzureCli        = (${InstallAzureCli} -eq 1)
$InstallVsCode          = (${InstallVsCode} -eq 1)
$InstallStorageExplorer = (${InstallStorageExplorer} -eq 1)
$InstallGit             = (${InstallGit} -eq 1)
$InstallPythonTools     = (${InstallPythonTools} -eq 1)
$InstallRTools          = (${InstallRTools} -eq 1)
$ConfigureConda         = (${CondaConfig} -eq 1)

# Only wait for (and pull from) Nexus when at least one Nexus-backed install/config action is enabled.
$NexusActionsEnabled    = $InstallAzureCli -or $InstallVsCode -or $InstallStorageExplorer -or `
                          $InstallGit -or $InstallPythonTools -or $InstallRTools -or $ConfigureConda

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

function Configure-CondaProxy {
  param(
    [string]$CondaExecutable = "conda"
  )

  try {
    & $CondaExecutable config --add channels ${nexus_proxy_url}/repository/conda-mirror/main/ --system
    & $CondaExecutable config --add channels ${nexus_proxy_url}/repository/conda-repo/main/ --system
    & $CondaExecutable config --remove channels defaults --system
    & $CondaExecutable config --set channel_alias ${nexus_proxy_url}/repository/conda-mirror/ --system
  }
  catch {
    Write-Host "WARNING: Failed to configure conda proxy using $CondaExecutable - $($_.Exception.Message)"
  }
}

function Configure-RProxy {
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
}

function New-DesktopShortcut {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$TargetPath,
    [string]$Arguments = "",
    [string]$WorkingDirectory = ""
  )

  # Best-effort - never fail VM configuration because of a shortcut.
  try {
    # Allow wildcard targets (tools whose install path contains a version).
    if ($TargetPath -match '[\*\?]') {
      $resolved = Get-ChildItem -Path $TargetPath -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($resolved) { $TargetPath = $resolved.FullName }
    }
    if (-not (Test-Path $TargetPath)) {
      Write-Host "Skipping desktop shortcut for $Name - target not found: $TargetPath"
      return
    }
    $desktop = "C:\Users\Public\Desktop"
    New-Item -ItemType Directory -Force -Path $desktop | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path $desktop "$Name.lnk"))
    $shortcut.TargetPath = $TargetPath
    if ($Arguments) { $shortcut.Arguments = $Arguments }
    if ($WorkingDirectory) { $shortcut.WorkingDirectory = $WorkingDirectory }
    else { $shortcut.WorkingDirectory = Split-Path $TargetPath -Parent }
    $shortcut.Save()
    Write-Host "Created desktop shortcut for $Name"
  }
  catch {
    Write-Host "WARNING: Failed to create desktop shortcut for $Name - $($_.Exception.Message)"
  }
}

# Make sure the proxy is up before pulling any of the installers below.
if ($NexusActionsEnabled) {
  Wait-ForNexus | Out-Null
}
else {
  Write-Host "No Nexus-backed install/config actions enabled - skipping the wait for the Nexus proxy."
}

# Configure conda on images that already include it.
if ($ConfigureConda)
{
  Configure-CondaProxy
}

# Configure any pre-existing R installations before tool install.
Configure-RProxy

$AzureCliMsi = Join-Path $ToolsDir "azure-cli.msi"
if ($InstallAzureCli) {
  Install-TreTool -Name "Azure CLI" `
    -Url "${nexus_proxy_url}/repository/azure-cli/azure-cli-$AzureCliVersion-x64.msi" `
    -OutFile $AzureCliMsi `
    -FilePath "msiexec.exe" `
    -ArgumentList @("/i", "`"$AzureCliMsi`"", "/qn", "/norestart")

  $env:Path = "$Env:ProgramFiles\Microsoft SDKs\Azure\CLI2\wbin;$Env:ProgramFiles (x86)\Microsoft SDKs\Azure\CLI2\wbin;$env:Path"
}

$VsCodeSetup = Join-Path $ToolsDir "vscode-setup.exe"
if ($InstallVsCode) {
  Install-TreTool -Name "Visual Studio Code" `
    -Url "${nexus_proxy_url}/repository/vscode/$VsCodeVersion/win32-x64/stable" `
    -OutFile $VsCodeSetup `
    -FilePath $VsCodeSetup `
    -ArgumentList @("/VERYSILENT", "/NORESTART", "/MERGETASKS=!runcode,addcontextmenufiles,addcontextmenufolders,addtopath")
}

# Azure Storage Explorer - proxied via the Nexus storage-explorer raw repository
$StorageExplorerSetup = Join-Path $ToolsDir "storage-explorer.exe"
if ($InstallStorageExplorer) {
  Install-TreTool -Name "Azure Storage Explorer" `
    -Url "${nexus_proxy_url}/repository/storage-explorer/v$StorageExplorerVersion/StorageExplorer-windows-x64.exe" `
    -OutFile $StorageExplorerSetup `
    -FilePath $StorageExplorerSetup `
    -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/ALLUSERS")
}

# Git for Windows - proxied via the Nexus git-download raw repository
$GitSetup = Join-Path $ToolsDir "git-setup.exe"
if ($InstallGit) {
  Install-TreTool -Name "Git" `
    -Url "${nexus_proxy_url}/repository/git-download/v$GitVersion.windows.1/Git-$GitVersion-64-bit.exe" `
    -OutFile $GitSetup `
    -FilePath $GitSetup `
    -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOCANCEL", "/SP-")
}

# Miniforge (conda-forge Python distribution) - proxied via the Nexus miniforge-download raw repository
$MiniforgeSetup = Join-Path $ToolsDir "miniforge-setup.exe"
if ($InstallPythonTools) {
  Install-TreTool -Name "Miniforge (Python)" `
    -Url "${nexus_proxy_url}/repository/miniforge-download/$MiniforgeVersion/Miniforge3-$MiniforgeVersion-Windows-x86_64.exe" `
    -OutFile $MiniforgeSetup `
    -FilePath $MiniforgeSetup `
    -ArgumentList @("/InstallationType=AllUsers", "/RegisterPython=1", "/AddToPath=1", "/S", "/D=$MiniforgePath")

  $MiniforgeConda = Join-Path $MiniforgePath "Scripts\conda.exe"
  if (Test-Path $MiniforgeConda) {
    Configure-CondaProxy -CondaExecutable $MiniforgeConda
  }
  else {
    Write-Host "Skipping Miniforge conda proxy configuration - conda not found at $MiniforgeConda"
  }

  # JupyterLab - installed into the Miniforge base environment via the Nexus PyPI proxy (pip.ini configured above)
  $MiniforgePip = Join-Path $MiniforgePath "Scripts\pip.exe"
  if (Test-Path $MiniforgePip) {
    try {
      Write-Host "Installing JupyterLab into the Miniforge base environment"
      & $MiniforgePip install --no-warn-script-location "jupyterlab==$JupyterLabVersion"
      if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: JupyterLab install exited with code $LASTEXITCODE" }
    }
    catch {
      Write-Host "WARNING: Failed to install JupyterLab - $($_.Exception.Message)"
    }
  }
  else {
    Write-Host "Skipping JupyterLab install - Miniforge pip not found at $MiniforgePip"
  }
}

# R (CRAN base) - proxied via the Nexus cran-r-download raw repository
$RSetup = Join-Path $ToolsDir "r-setup.exe"
if ($InstallRTools) {
  Install-TreTool -Name "R" `
    -Url "${nexus_proxy_url}/repository/cran-r-download/bin/windows/base/old/$RVersion/R-$RVersion-win.exe" `
    -OutFile $RSetup `
    -FilePath $RSetup `
    -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-")

  # Ensure the newly installed R gets the CRAN proxy config too.
  Configure-RProxy
}

# RStudio Desktop (open source) - proxied via the Nexus r-studio-download raw repository
$RStudioSetup = Join-Path $ToolsDir "rstudio-setup.exe"
if ($InstallRTools) {
  Install-TreTool -Name "RStudio Desktop" `
    -Url "${nexus_proxy_url}/repository/r-studio-download/electron/windows/RStudio-$RStudioVersion.exe" `
    -OutFile $RStudioSetup `
    -FilePath $RStudioSetup `
    -ArgumentList @("/S")
}

# Create desktop shortcuts for the installed GUI tools (best-effort; missing tools are skipped)
if ($InstallVsCode) {
  New-DesktopShortcut -Name "Visual Studio Code" -TargetPath "$Env:ProgramFiles\Microsoft VS Code\Code.exe"
}
if ($InstallStorageExplorer) {
  New-DesktopShortcut -Name "Azure Storage Explorer" -TargetPath "$Env:ProgramFiles\Microsoft Azure Storage Explorer\StorageExplorer.exe"
}
if ($InstallRTools) {
  New-DesktopShortcut -Name "RStudio" -TargetPath "$Env:ProgramFiles\RStudio\rstudio.exe"
}
# Note: the R installer already creates its own versioned desktop shortcut (e.g. "R 4.6.1"), so we don't add another.
if ($InstallGit) {
  New-DesktopShortcut -Name "Git Bash" -TargetPath "$Env:ProgramFiles\Git\git-bash.exe"
}
if ($InstallPythonTools) {
  New-DesktopShortcut -Name "JupyterLab" -TargetPath "$MiniforgePath\Scripts\jupyter-lab.exe" -WorkingDirectory "%USERPROFILE%"
}
