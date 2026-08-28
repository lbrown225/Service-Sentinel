[CmdletBinding()]
param(
    [string]$Endpoint = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Endpoint)) {
    $Endpoint = (& terraform -chdir=terraform output -raw health_endpoint) -join ""

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read health_endpoint from Terraform output."
    }
}

$responseBody = (& curl.exe `
    --fail-with-body `
    --silent `
    --show-error `
    $Endpoint) -join [Environment]::NewLine

if ($LASTEXITCODE -ne 0) {
    throw "Production health request failed."
}

$healthResponse = $responseBody | ConvertFrom-Json
$expectedFields = @("service", "status", "version")
$actualFields = @($healthResponse.PSObject.Properties.Name | Sort-Object)
$fieldDifference = Compare-Object $expectedFields $actualFields

if ($fieldDifference) {
    throw "Unexpected health response fields: $($actualFields -join ', ')"
}

if (
    $healthResponse.status -ne "healthy" -or
    $healthResponse.service -ne "service-sentinel-api" -or
    $healthResponse.version -ne "0.1.0"
) {
    throw "Unexpected health response body: $responseBody"
}

[pscustomobject]@{
    Endpoint = $Endpoint
    Status   = $healthResponse.status
    Service  = $healthResponse.service
    Version  = $healthResponse.version
}
