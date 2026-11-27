param(
    [Parameter(Mandatory)][ValidatePattern('^stgws[a-z0-9]{4}$')][string]$Account,
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$Share,
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{32}$')][string]$ProbeId,
    [Parameter(Mandatory)][ValidateSet('access', 'write', 'change', 'read')][string]$Phase
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$stage = 'private-dns'
$file = "https://$Account.file.core.windows.net/$Share/e2e-$ProbeId.txt"

function Assert-PrivateDns([string]$Url) {
    $addresses = [System.Net.Dns]::GetHostAddresses(([uri]$Url).Host)
    if ($addresses.Count -eq 0) { throw 'No address' }
    foreach ($address in $addresses) {
        $bytes = $address.GetAddressBytes()
        $private = $bytes.Length -eq 4 -and (
            $bytes[0] -eq 10 -or
            ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
            ($bytes[0] -eq 192 -and $bytes[1] -eq 168)
        )
        if (-not $private) { throw 'DNS is not private' }
    }
}

function Get-FileHeaders {
    $identity = Invoke-RestMethod -Headers @{Metadata = 'true'} -Uri 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fstorage.azure.com%2F' -TimeoutSec 15
    # Azure Files accepts an Entra ID token on the REST API only with the backup intent.
    return @{
        Authorization = "Bearer $($identity.access_token)"
        'x-ms-version' = '2022-11-02'
        'x-ms-file-request-intent' = 'backup'
        'x-ms-date' = [DateTime]::UtcNow.ToString('R')
    }
}

function Get-Status([string]$Method, [string]$Uri, [hashtable]$Headers) {
    try {
        return [int](Invoke-WebRequest -UseBasicParsing -Method $Method -Uri $Uri -Headers $Headers -TimeoutSec 30).StatusCode
    } catch {
        # Windows PowerShell and PowerShell 7 use different exception types, but both have a Response.
        $response = $_.Exception.Response
        if ($null -eq $response) { throw }
        return [int]$response.StatusCode
    }
}

function Write-ProbeFile([string]$Text) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $headers = Get-FileHeaders
    $headers['x-ms-type'] = 'file'
    $headers['x-ms-content-length'] = "$($bytes.Length)"
    $null = Invoke-WebRequest -UseBasicParsing -Method Put -Uri $file -Headers $headers -Body ([byte[]]@()) -TimeoutSec 30
    $headers = Get-FileHeaders
    $headers['x-ms-range'] = "bytes=0-$($bytes.Length - 1)"
    $headers['x-ms-write'] = 'update'
    $null = Invoke-WebRequest -UseBasicParsing -Method Put -Uri "${file}?comp=range" -Headers $headers -Body $bytes -ContentType 'application/octet-stream' -TimeoutSec 30
}

function Read-ProbeFile {
    $response = Invoke-WebRequest -UseBasicParsing -Method Get -Uri $file -Headers (Get-FileHeaders) -TimeoutSec 30
    $stream = New-Object System.IO.MemoryStream
    $response.RawContentStream.CopyTo($stream)
    return [Text.Encoding]::UTF8.GetString($stream.ToArray())
}

try {
    Assert-PrivateDns $file
    $result = [ordered]@{phase = $Phase; probe = $ProbeId; private_dns = $true}
    if ($Phase -eq 'access') {
        $stage = 'file-unassigned'
        $result.unassigned = Get-Status 'Get' $file (Get-FileHeaders)
    } else {
        $stage = 'file-role'
        # A new role assignment can take some minutes to apply.
        $deadline = [DateTime]::UtcNow.AddMinutes(10)
        while ((Get-Status 'Get' "https://$Account.file.core.windows.net/${Share}?restype=directory&comp=list" (Get-FileHeaders)) -ne 200) {
            if ([DateTime]::UtcNow -ge $deadline) { throw 'Role did not apply' }
            Start-Sleep -Seconds 20
        }
        $expected = $ProbeId
        if ($Phase -eq 'write') {
            $stage = 'file-write'
            Write-ProbeFile $ProbeId
        } elseif ($Phase -eq 'change') {
            $stage = 'file-change'
            $expected = "changed-$ProbeId"
            Write-ProbeFile $expected
        }
        $stage = 'file-read'
        $result.matches = (Read-ProbeFile) -eq $expected
    }
    Write-Output ('BACKUP_PROBE_RESULT=' + ($result | ConvertTo-Json -Compress))
} catch {
    # Do not emit exception details or tokens.
    Write-Output "BACKUP_PROBE_FAILED=$stage"
    exit 1
} finally {
    $identity = $null
}
