$PipConfigFolderPath = "C:\ProgramData\pip\"
If(!(Test-Path $PipConfigFolderPath))
{
  New-Item -ItemType Directory -Force -Path $PipConfigFolderPath
}

$PipConfigFilePath = $PipConfigFolderPath + "pip.ini"

$ConfigBody = @"
[global]
index = url/repository/pypi/pypi
index-url = url/repository/pypi/simple
trusted-host = url
"@

Out-File -FilePath $PipConfigFilePath -InputObject $ConfigBody
