$ErrorActionPreference = "Stop"

# Configure pip to use Nexus proxy
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

# Download review data
$DownloadPath = $env:Public + "\Desktop\ReviewData"
mkdir $DownloadPath
az storage blob download-batch -d $DownloadPath -s '"${airlock_request_sas_url}"'
