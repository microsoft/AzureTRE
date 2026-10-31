param(
    [Parameter(Mandatory)][ValidatePattern('^https://[a-z0-9-]+\.fhir\.azurehealthcareapis\.com$')][string]$FhirUrl,
    [ValidatePattern('^(https://[a-z0-9-]+\.dicom\.azurehealthcareapis\.com)?$')][string]$DicomUrl = '',
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{32}$')][string]$ProbeId,
    [Parameter(Mandatory)][ValidateSet('access', 'write', 'read')][string]$Phase
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$stage = 'private-dns'

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

function Get-Status([string]$Uri, [hashtable]$Headers = @{}) {
    try {
        return [int](Invoke-WebRequest -UseBasicParsing -Uri $Uri -Headers $Headers -TimeoutSec 30).StatusCode
    } catch {
        # Windows PowerShell and PowerShell 7 use different exception types, but both have a Response.
        $response = $_.Exception.Response
        if ($null -eq $response) { throw }
        return [int]$response.StatusCode
    }
}

function Get-FhirHeaders {
    $resource = [uri]::EscapeDataString($FhirUrl)
    $identity = Invoke-RestMethod -Headers @{Metadata = 'true'} -Uri "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=$resource" -TimeoutSec 15
    return @{Authorization = "Bearer $($identity.access_token)"}
}

function Invoke-Fhir([hashtable]$Request, [int[]]$RetryStatus) {
    # A 200 in the role wait does not prove that each later request gets the new role.
    while ($true) {
        try {
            return Invoke-RestMethod @Request -Headers (Get-FhirHeaders) -TimeoutSec 30
        } catch {
            $response = $_.Exception.Response
            if ($null -eq $response -or [int]$response.StatusCode -notin $RetryStatus -or [DateTime]::UtcNow -ge $deadline) { throw }
            Start-Sleep -Seconds 20
        }
    }
}

function Get-ProbeCount {
    # A search changes no data, so throttling and server errors are also tried again.
    $search = Invoke-Fhir -Request @{Uri = "$FhirUrl/Patient?identifier=urn:tre:e2e|$ProbeId"} -RetryStatus 403, 429, 500, 502, 503, 504
    if ($search.resourceType -ne 'Bundle') { throw 'Unexpected search result' }
    return @($search.entry).Where({ $null -ne $_ }).Count
}

try {
    Assert-PrivateDns $FhirUrl
    $result = [ordered]@{phase = $Phase; probe = $ProbeId; private_dns = $true}
    if ($Phase -eq 'access') {
        $stage = 'fhir-metadata'
        $metadata = Invoke-RestMethod -Uri "$FhirUrl/metadata" -TimeoutSec 30
        if ($metadata.resourceType -ne 'CapabilityStatement') { throw 'Unexpected metadata' }
        $result.fhir_version = [string]$metadata.fhirVersion
        $stage = 'fhir-anonymous'
        $result.anonymous = Get-Status "$FhirUrl/Patient?_count=1"
        $stage = 'fhir-unassigned'
        $result.unassigned = Get-Status "$FhirUrl/Patient?_count=1" (Get-FhirHeaders)
    } else {
        $stage = 'fhir-role'
        # A new role assignment can take some minutes to apply.
        $deadline = [DateTime]::UtcNow.AddMinutes(10)
        while ((Get-Status "$FhirUrl/Patient?_count=1" (Get-FhirHeaders)) -ne 200) {
            if ([DateTime]::UtcNow -ge $deadline) { throw 'Role did not apply' }
            Start-Sleep -Seconds 20
        }
        if ($Phase -eq 'write') {
            $stage = 'fhir-write'
            $patient = @{resourceType = 'Patient'; identifier = @(@{system = 'urn:tre:e2e'; value = $ProbeId})} | ConvertTo-Json -Depth 4
            # FHIR writes nothing for a refused (403) or throttled (429) create, so only these are tried again.
            $create = @{Method = 'Post'; ContentType = 'application/fhir+json'; Uri = "$FhirUrl/Patient"; Body = $patient}
            $created = Invoke-Fhir -Request $create -RetryStatus 403, 429
            if ($created.resourceType -ne 'Patient') { throw 'Unexpected create result' }
        }
        $stage = 'fhir-read'
        $result.count = Get-ProbeCount
        if ($DicomUrl) {
            $stage = 'dicom-access'
            Assert-PrivateDns $DicomUrl
            $result.dicom_anonymous = Get-Status "$DicomUrl/v2/studies"
        }
    }
    Write-Output ('HEALTH_PROBE_RESULT=' + ($result | ConvertTo-Json -Compress))
} catch {
    # Do not emit exception details or tokens. The HTTP status of a failed request is safe to emit.
    $response = $_.Exception.Response
    Write-Output "HEALTH_PROBE_FAILED=$stage"
    if ($null -ne $response) { Write-Output "HEALTH_PROBE_STATUS=$([int]$response.StatusCode)" }
    exit 1
}
