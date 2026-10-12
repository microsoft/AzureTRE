param(
    [Parameter(Mandatory)][ValidateSet('upload', 'read')][string]$Phase,
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{32}$')][string]$ProbeId,
    [Parameter(Mandatory)][ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$')][string]$BlobName,
    [Parameter(Mandatory)][string]$ContentBase64,
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedSha256,
    [string]$ContainerUrl
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$stage = 'parameters'
$response = $null
$stream = $null
$sha = $null
try {
    if ($BlobName.EndsWith('.') -or $BlobName -match '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)') {
        throw 'Invalid Windows file name'
    }
    $bytes = [Convert]::FromBase64String($ContentBase64)
    if ($bytes.Length -eq 0 -or $bytes.Length -gt 16384) { throw 'Invalid synthetic content size' }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $hash = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant()
    if ($hash -cne $ExpectedSha256) { throw 'Input content hash mismatch' }
    if ($Phase -eq 'upload') {
        # The SAS is supplied as a protected Run Command parameter, never in source.
        $uri = [Uri]$ContainerUrl
        if (
            $uri.Scheme -cne 'https' -or
            $uri.Authority -cnotmatch '^[a-z0-9]{3,24}\.blob\.core\.windows\.net$' -or
            $uri.AbsolutePath -cnotmatch '^/[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$' -or
            $uri.AbsolutePath.Contains('--') -or
            $uri.Query -notmatch '(^\?|&)sig=[^&]+' -or
            $uri.Fragment -ne '' -or $ContainerUrl -match '\s'
        ) { throw 'Invalid container URL' }
        $stage = 'private-dns'
        $addresses = [System.Net.Dns]::GetHostAddresses($uri.DnsSafeHost)
        if ($addresses.Count -eq 0) { throw 'No blob address' }
        foreach ($address in $addresses) {
            $parts = $address.GetAddressBytes()
            $private = $parts.Length -eq 4 -and (
                $parts[0] -eq 10 -or
                ($parts[0] -eq 172 -and $parts[1] -ge 16 -and $parts[1] -le 31) -or
                ($parts[0] -eq 192 -and $parts[1] -eq 168)
            )
            if (-not $private) { throw 'Blob DNS is not private' }
        }
        $stage = 'upload'
        $blobUrl = $uri.GetLeftPart([UriPartial]::Path) + '/' + $BlobName + $uri.Query
        $deadline = [DateTime]::UtcNow.AddMinutes(5)
        do {
            $retry = $false
            try {
                $request = [System.Net.HttpWebRequest]::Create($blobUrl)
                $request.Method = 'PUT'
                $request.AllowAutoRedirect = $false
                $request.Timeout = 30000
                $request.ReadWriteTimeout = 30000
                $request.ContentType = 'application/octet-stream'
                $request.ContentLength = $bytes.Length
                $request.Headers['x-ms-version'] = '2021-12-02'
                $request.Headers['x-ms-blob-type'] = 'BlockBlob'
                $stream = $request.GetRequestStream()
                $stream.Write($bytes, 0, $bytes.Length)
                $stream.Dispose()
                $stream = $null
                $response = $request.GetResponse()
                if ([int]$response.StatusCode -ne 201) { throw 'Unexpected upload status' }
            } catch [System.Net.WebException] {
                $response = $_.Exception.Response
                # Retry only the draft-container creation race. Do not retry access failures.
                $retry = $null -ne $response -and [int]$response.StatusCode -eq 404 -and
                    $response.Headers['x-ms-error-code'] -ceq 'ContainerNotFound'
                if (-not $retry -or [DateTime]::UtcNow -ge $deadline) { throw 'Blob upload failed' }
            } finally {
                if ($null -ne $stream) { $stream.Dispose(); $stream = $null }
                if ($null -ne $response) { $response.Dispose(); $response = $null }
            }
            if ($retry) { Start-Sleep -Seconds 10 }
        } while ($retry)
    } else {
        if ($ContainerUrl) { throw 'Read probes must not receive a container URL' }
        $stage = 'review-file'
        $file = Join-Path 'C:\Users\Public\Desktop\ReviewData' $BlobName
        # Inspect the copy made by the review-VM bundle. Do not download a replacement.
        if (-not [System.IO.File]::Exists($file)) { throw 'Review file is missing' }
        $fileInfo = Get-Item -LiteralPath $file
        if (($fileInfo.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Review file is a link' }
        if ($fileInfo.Length -ne $bytes.Length) { throw 'Review content size mismatch' }
        $actual = [System.IO.File]::ReadAllBytes($file)
        $hash = [BitConverter]::ToString($sha.ComputeHash($actual)).Replace('-', '').ToLowerInvariant()
        if ($hash -cne $ExpectedSha256) { throw 'Review content hash mismatch' }
    }
    $result = @{phase = $Phase; probe = $ProbeId; sha256 = $hash}
    Write-Output ('AIRLOCK_PROBE_RESULT=' + ($result | ConvertTo-Json -Compress))
} catch {
    # Do not emit exception text, request URLs, SAS tokens or response bodies.
    Write-Output "AIRLOCK_PROBE_FAILED=$stage"
    exit 1
} finally {
    if ($null -ne $stream) { $stream.Dispose() }
    if ($null -ne $response) { $response.Dispose() }
    if ($null -ne $sha) { $sha.Dispose() }
    $ContainerUrl = $null
    $blobUrl = $null
    $uri = $null
    $request = $null
}
