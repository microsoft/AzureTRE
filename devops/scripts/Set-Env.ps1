# This script loads environment variables from a file and is the PowerShell counterpart of load_env.sh.
# Usage: .\Set-Env.ps1 <path to .env file>

$EnvFilePath = $args[0]
$EnvFileContent = Get-Content -Path $EnvFilePath

$EnvFileContent | ForEach-Object {
    $KeyValue = $_ -split "=", 2
    [Environment]::SetEnvironmentVariable($KeyValue[0], $KeyValue[1])
    Write-Output "Set $($KeyValue[0]) (value has length $($KeyValue[1].length))"
}
