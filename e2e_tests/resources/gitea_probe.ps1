param(
    [Parameter(Mandatory)][ValidatePattern('^https://gitea-[a-z0-9-]+\.azurewebsites\.net$')][string]$GiteaUrl,
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$VaultName,
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$SecretName,
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{32}$')][string]$ProbeId,
    [Parameter(Mandatory)][ValidateSet('write', 'read')][string]$Phase
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
# The Gitea web app accepts only TLS 1.3.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
$stage = 'private-dns'
$api = "$GiteaUrl/api/v1"
$admin = 'giteaadmin'
$repository = "$api/repos/$admin/e2e-$ProbeId"

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

function Get-Status([string]$Method, [string]$Uri, [hashtable]$Headers = @{}, [string]$Body = '') {
    $request = @{UseBasicParsing = $true; Method = $Method; Uri = $Uri; Headers = $Headers; TimeoutSec = 30}
    if ($Body) {
        $request.Body = $Body
        $request.ContentType = 'application/json'
    }
    try {
        return [int](Invoke-WebRequest @request).StatusCode
    } catch {
        # Windows PowerShell and PowerShell 7 use different exception types, but both have a Response.
        $response = $_.Exception.Response
        if ($null -eq $response) { throw }
        return [int]$response.StatusCode
    }
}

function Wait-Ok([string]$Uri, [hashtable]$Headers = @{}) {
    # The app can take some minutes to start, and its start script creates the admin user after that.
    $deadline = [DateTime]::UtcNow.AddMinutes(15)
    while ($true) {
        try {
            if ((Get-Status 'GET' $Uri $Headers) -eq 200) { return }
        } catch {
            # A connection error during a restart is the same as not ready.
        }
        if ([DateTime]::UtcNow -ge $deadline) { throw 'Not ready' }
        Start-Sleep -Seconds 20
    }
}

function Get-Password {
    # A new role assignment can take some minutes to apply.
    $deadline = [DateTime]::UtcNow.AddMinutes(10)
    while ($true) {
        try {
            $identity = Invoke-RestMethod -Headers @{Metadata = 'true'} -Uri 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net' -TimeoutSec 15
            $secret = Invoke-RestMethod -Headers @{Authorization = "Bearer $($identity.access_token)"} -Uri "https://$VaultName.vault.azure.net/secrets/${SecretName}?api-version=7.4" -TimeoutSec 15
            return $secret.value
        } catch {
            if ([DateTime]::UtcNow -ge $deadline) { throw 'Secret access did not become ready' }
            Start-Sleep -Seconds 20
        }
    }
}

function Get-AdminHeaders([string]$Password) {
    $pair = [Text.Encoding]::UTF8.GetBytes("${admin}:$Password")
    return @{Authorization = 'Basic ' + [Convert]::ToBase64String($pair)}
}

try {
    Assert-PrivateDns $GiteaUrl
    $result = [ordered]@{phase = $Phase; probe = $ProbeId; private_dns = $true}
    $stage = 'gitea-ready'
    Wait-Ok "$api/version"
    $stage = 'secret-access'
    $headers = Get-AdminHeaders (Get-Password)
    $stage = 'gitea-admin'
    Wait-Ok "$api/user" $headers
    if ($Phase -eq 'write') {
        $stage = 'gitea-anonymous'
        $result.anonymous_create = Get-Status 'POST' "$api/user/repos" @{} (@{name = "e2e-$ProbeId"} | ConvertTo-Json)
        $stage = 'gitea-wrong-password'
        $result.wrong_password = Get-Status 'GET' "$api/user" (Get-AdminHeaders ([guid]::NewGuid().ToString()))
        $stage = 'gitea-write'
        $body = @{name = "e2e-$ProbeId"; private = $true; auto_init = $true} | ConvertTo-Json
        $created = Invoke-RestMethod -Method Post -Headers $headers -ContentType 'application/json' -Uri "$api/user/repos" -Body $body -TimeoutSec 30
        if ($created.name -ne "e2e-$ProbeId") { throw 'Unexpected repository' }
        $content = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($ProbeId))
        $file = @{content = $content; message = 'E2E probe'} | ConvertTo-Json
        $null = Invoke-RestMethod -Method Post -Headers $headers -ContentType 'application/json' -Uri "$repository/contents/probe.txt" -Body $file -TimeoutSec 30
        $stage = 'gitea-private'
        $result.anonymous_read = Get-Status 'GET' $repository
    }
    $stage = 'gitea-read'
    $text = Invoke-RestMethod -Headers $headers -Uri "$repository/raw/probe.txt" -TimeoutSec 30
    $result.content = ([string]$text).Trim() -eq $ProbeId
    if ($Phase -eq 'read') {
        $stage = 'gitea-delete'
        $null = Invoke-RestMethod -Method Delete -Headers $headers -Uri $repository -TimeoutSec 30
        $result.deleted = (Get-Status 'GET' $repository $headers) -eq 404
    }
    Write-Output ('GITEA_PROBE_RESULT=' + ($result | ConvertTo-Json -Compress))
} catch {
    # Do not emit exception details, passwords or tokens.
    Write-Output "GITEA_PROBE_FAILED=$stage"
    exit 1
} finally {
    $identity = $null
    $secret = $null
    $headers = $null
}
