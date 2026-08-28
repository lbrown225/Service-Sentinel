[CmdletBinding()]
param(
    [string]$FunctionName = "service-sentinel-api",
    [string]$Alias = "candidate",
    [string]$ExpectedVersion = "",
    [string]$Profile = "service-sentinel",
    [string]$Region = "us-west-1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$awsCommand = Get-Command aws -ErrorAction Stop
$now = [DateTimeOffset]::UtcNow
$lambdaEvent = @{
    version = "2.0"
    routeKey = "GET /health"
    rawPath = "/health"
    rawQueryString = ""
    headers = @{
        host = "candidate.internal"
    }
    requestContext = @{
        accountId = "smoke-test"
        apiId = "smoke-test"
        domainName = "candidate.internal"
        domainPrefix = "candidate"
        http = @{
            method = "GET"
            path = "/health"
            protocol = "HTTP/1.1"
            sourceIp = "127.0.0.1"
            userAgent = "invoke-candidate.ps1"
        }
        requestId = "candidate-$($now.ToUnixTimeMilliseconds())"
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

$temporaryDirectory = Join-Path `
    ([IO.Path]::GetTempPath()) `
    "service-sentinel-smoke-$([guid]::NewGuid().ToString('N'))"
$payloadPath = Join-Path $temporaryDirectory "event.json"
$responsePath = Join-Path $temporaryDirectory "response.json"

try {
    [IO.Directory]::CreateDirectory($temporaryDirectory) | Out-Null

    $lambdaEventJson = $lambdaEvent | ConvertTo-Json -Depth 10 -Compress
    [IO.File]::WriteAllText(
        $payloadPath,
        $lambdaEventJson,
        [Text.UTF8Encoding]::new($false)
    )

    $metadataJson = (& $awsCommand.Source lambda invoke `
        --function-name $FunctionName `
        --qualifier $Alias `
        --invocation-type RequestResponse `
        --cli-binary-format raw-in-base64-out `
        --payload "fileb://$payloadPath" `
        --region $Region `
        --profile $Profile `
        $responsePath) -join [Environment]::NewLine

    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI Lambda invocation failed."
    }

    $metadata = $metadataJson | ConvertFrom-Json

    if ($metadata.StatusCode -ne 200) {
        throw "AWS invocation status was $($metadata.StatusCode)."
    }

    $functionError = $metadata.PSObject.Properties["FunctionError"]

    if ($functionError -and $functionError.Value) {
        throw "Lambda reported FunctionError: $($functionError.Value)"
    }

    if (
        $ExpectedVersion -and
        $metadata.ExecutedVersion -ne $ExpectedVersion
    ) {
        throw (
            "Expected Lambda version $ExpectedVersion, " +
            "but executed version $($metadata.ExecutedVersion)."
        )
    }

    $lambdaResponse = Get-Content -LiteralPath $responsePath -Raw |
        ConvertFrom-Json

    if ($lambdaResponse.statusCode -ne 200) {
        throw (
            "Handler returned HTTP $($lambdaResponse.statusCode): " +
            $lambdaResponse.body
        )
    }

    $healthResponse = $lambdaResponse.body | ConvertFrom-Json
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
        throw "Unexpected health response body: $($lambdaResponse.body)"
    }

    [pscustomobject]@{
        InvokeStatusCode = $metadata.StatusCode
        ExecutedVersion = $metadata.ExecutedVersion
        HttpStatusCode = $lambdaResponse.statusCode
        Status = $healthResponse.status
        Service = $healthResponse.service
        Version = $healthResponse.version
    }
}
finally {
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}
