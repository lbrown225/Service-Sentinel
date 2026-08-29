[CmdletBinding()]
param(
    [string]$FunctionName = "service-sentinel-api",
    [string]$Alias = "candidate",
    [string]$ExpectedVersion = "",
    [ValidateSet("health", "status")]
    [string]$Route = "health",
    [string]$Profile = "service-sentinel",
    [string]$Region = "us-west-1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$awsCommand = Get-Command aws -ErrorAction Stop
$now = [DateTimeOffset]::UtcNow
$requestPath = "/$Route"
$routeKey = "GET $requestPath"
$lambdaEvent = @{
    version = "2.0"
    routeKey = $routeKey
    rawPath = $requestPath
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
            path = $requestPath
            protocol = "HTTP/1.1"
            sourceIp = "127.0.0.1"
            userAgent = "invoke-candidate.ps1"
        }
        requestId = "candidate-$Route-$($now.ToUnixTimeMilliseconds())"
        routeKey = $routeKey
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

    $apiResponse = $lambdaResponse.body | ConvertFrom-Json
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
        throw "Unexpected $Route response body: $($lambdaResponse.body)"
    }

    $version = $null
    $checkedAt = $null

    if ($Route -eq "health") {
        if (
            $apiResponse.status -ne "healthy" -or
            $apiResponse.version -ne "0.1.0"
        ) {
            throw "Unexpected health response body: $($lambdaResponse.body)"
        }

        $version = $apiResponse.version
    }
    else {
        if (
            $apiResponse.status -ne "UNKNOWN" -or
            $null -ne $apiResponse.checked_at
        ) {
            throw "Unexpected status response body: $($lambdaResponse.body)"
        }

        $checkedAt = $apiResponse.checked_at
    }

    [pscustomobject]@{
        Route = $requestPath
        InvokeStatusCode = $metadata.StatusCode
        ExecutedVersion = $metadata.ExecutedVersion
        HttpStatusCode = $lambdaResponse.statusCode
        Status = $apiResponse.status
        Service = $apiResponse.service
        Version = $version
        CheckedAt = $checkedAt
    }
}
finally {
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}
