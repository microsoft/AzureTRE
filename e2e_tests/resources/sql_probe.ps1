param(
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+\.database\.windows\.net$')][string]$Server,
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$VaultName,
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$SecretName,
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{32}$')][string]$ProbeId,
    [Parameter(Mandatory)][ValidateSet('write', 'read')][string]$Phase,
    [Parameter(Mandatory)][ValidateSet('S1', 'S2')][string]$ExpectedSku
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$connection = $null
$stage = 'private-dns'
try {
    $addresses = [System.Net.Dns]::GetHostAddresses($Server)
    if ($addresses.Count -eq 0) { throw 'No SQL address' }
    foreach ($address in $addresses) {
        $bytes = $address.GetAddressBytes()
        $private = $bytes.Length -eq 4 -and (
            $bytes[0] -eq 10 -or
            ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
            ($bytes[0] -eq 192 -and $bytes[1] -eq 168)
        )
        if (-not $private) { throw 'SQL DNS is not private' }
    }
    $stage = 'secret-access'
    $secret = $null
    $deadline = [DateTime]::UtcNow.AddMinutes(5)
    do {
        try {
            $identity = Invoke-RestMethod -Headers @{Metadata = 'true'} -Uri 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net' -TimeoutSec 15
            $secret = Invoke-RestMethod -Headers @{Authorization = "Bearer $($identity.access_token)"} -Uri "https://$VaultName.vault.azure.net/secrets/${SecretName}?api-version=7.4" -TimeoutSec 15
        } catch {
            if ([DateTime]::UtcNow -ge $deadline) { throw 'Secret access did not become ready' }
            Start-Sleep -Seconds 10
        }
    } while ($null -eq $secret)
    $stage = 'sql-connect'
    $builder = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
    $builder['Data Source'] = "tcp:$Server,1433"
    $builder['Initial Catalog'] = 'tredb'
    $builder['User ID'] = 'azuresqladmin'
    $builder['Password'] = $secret.value
    $builder['Encrypt'] = $true
    $builder['TrustServerCertificate'] = $false
    $builder['Connect Timeout'] = 30
    $connection = New-Object System.Data.SqlClient.SqlConnection($builder.ConnectionString)
    $connection.Open()
    $stage = 'sql-data'
    $command = $connection.CreateCommand()
    $command.CommandTimeout = 60
    $null = $command.Parameters.Add('@probe', [System.Data.SqlDbType]::VarChar, 32)
    $command.Parameters['@probe'].Value = $ProbeId
    if ($Phase -eq 'write') {
        $command.CommandText = 'CREATE TABLE dbo.tre_e2e_probe (probe varchar(32) NOT NULL PRIMARY KEY); INSERT INTO dbo.tre_e2e_probe (probe) VALUES (@probe);'
        $null = $command.ExecuteNonQuery()
    }
    $command.CommandText = 'SELECT COUNT(*) FROM dbo.tre_e2e_probe WHERE probe = @probe'
    $count = [int]$command.ExecuteScalar()
    if ($count -ne 1) { throw 'Expected SQL row is missing' }
    $command.CommandText = "SELECT CAST(DATABASEPROPERTYEX(DB_NAME(), 'ServiceObjective') AS nvarchar(128))"
    $sku = [string]$command.ExecuteScalar()
    if ($sku -ne $ExpectedSku) { throw 'Unexpected SQL SKU' }
    $result = @{phase = $Phase; probe = $ProbeId; sku = $sku; row_count = $count; private_dns = $true}
    Write-Output ('SQL_PROBE_RESULT=' + ($result | ConvertTo-Json -Compress))
} catch {
    # Do not emit exception details, tokens, connection strings or secret values.
    Write-Output "SQL_PROBE_FAILED=$stage"
    exit 1
} finally {
    if ($null -ne $connection) { $connection.Dispose() }
    $secret = $null
    $identity = $null
    $builder = $null
}
