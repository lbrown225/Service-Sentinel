[CmdletBinding()]
param(
    [ValidateSet("health", "status")]
    [string]$Route = "health",
    [string]$Endpoint = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Endpoint)) {
    $healthEndpoint = (& terraform -chdir=terraform output -raw health_endpoint) -join ""

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read health_endpoint from Terraform output."
    }

    $Endpoint = $healthEndpoint -replace "/health$", "/$Route"
}

$responseBody = (& curl.exe `
    --fail-with-body `
    --silent `
    --show-error `
    $Endpoint) -join [Environment]::NewLine

if ($LASTEXITCODE -ne 0) {
    throw "Production $Route request failed."
}

$apiResponse = $responseBody | ConvertFrom-Json
$expectedFields = if ($Route -eq "health") {
    @("service", "status", "version")
}
else {
    @("checked_at", "service", "status")
}
$actualFields = @($apiResponse.PSObject.Properties.Name | Sort-Object)
$fieldDifference = Compare-Object $expectedFields $actualFields

if ($fieldDifference) {
    throw "Unexpected $Route response fields: $($actualFields -join ', ')"
}

if ($apiResponse.service -ne "service-sentinel-api") {
    throw "Unexpected $Route response body: $responseBody"
}

$version = $null
$checkedAt = $null

if ($Route -eq "health") {
    if (
        $apiResponse.status -ne "healthy" -or
        $apiResponse.version -ne "0.1.0"
    ) {
        throw "Unexpected health response body: $responseBody"
    }

    $version = $apiResponse.version
}
else {
    if (
        $apiResponse.status -ne "UNKNOWN" -or
        $null -ne $apiResponse.checked_at
    ) {
        throw "Unexpected status response body: $responseBody"
    }

    $checkedAt = $apiResponse.checked_at
}

[pscustomobject]@{
    Route     = "/$Route"
    Endpoint  = $Endpoint
    Status    = $apiResponse.status
    Service   = $apiResponse.service
    Version   = $version
    CheckedAt = $checkedAt
}
