[CmdletBinding()]
param(
    [string]$InvocationUri = "http://localhost:9000/2015-03-31/functions/function/invocations"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$now = [DateTimeOffset]::UtcNow
$lambdaEvent = @{
    version = "2.0"
    routeKey = "GET /health"
    rawPath = "/health"
    rawQueryString = ""
    headers = @{
        host = "localhost"
    }
    requestContext = @{
        accountId = "local"
        apiId = "local"
        domainName = "localhost"
        domainPrefix = "localhost"
        http = @{
            method = "GET"
            path = "/health"
            protocol = "HTTP/1.1"
            sourceIp = "127.0.0.1"
            userAgent = "smoke-api-local-container.ps1"
        }
        requestId = "local-$($now.ToUnixTimeMilliseconds())"
        routeKey = "GET /health"
        stage = '$default'
        time = $now.ToString(
            "dd/MMM/yyyy:HH:mm:ss +0000",
            [Globalization.CultureInfo]::InvariantCulture
        )
        timeEpoch = $now.ToUnixTimeMilliseconds()
    }
    isBase64Encoded = $false
}

$lambdaEventJson = $lambdaEvent | ConvertTo-Json -Depth 10 -Compress

try {
    $lambdaResponse = Invoke-RestMethod `
        -Method Post `
        -Uri $InvocationUri `
        -ContentType "application/json" `
        -Body $lambdaEventJson
}
catch {
    throw "Local Lambda invocation failed. Is service-sentinel-local running? $($_.Exception.Message)"
}

if ($lambdaResponse -is [string]) {
    $lambdaResponse = $lambdaResponse | ConvertFrom-Json
}

if ($lambdaResponse.statusCode -ne 200) {
    throw "Lambda returned status code $($lambdaResponse.statusCode): $($lambdaResponse.body)"
}

$healthResponse = $lambdaResponse.body | ConvertFrom-Json

[pscustomobject]@{
    LambdaStatusCode = $lambdaResponse.statusCode
    Status = $healthResponse.status
    Service = $healthResponse.service
    Version = $healthResponse.version
}
