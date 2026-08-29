[CmdletBinding()]
param(
    [string]$FunctionName = "service-sentinel-monitor",
    [string]$Alias = "candidate",
    [string]$ExpectedVersion = "",
    [string]$Profile = "service-sentinel",
    [string]$Region = "us-west-1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$awsCommand = Get-Command aws -ErrorAction Stop
$temporaryDirectory = Join-Path `
    ([IO.Path]::GetTempPath()) `
    "service-sentinel-monitor-smoke-$([guid]::NewGuid().ToString('N'))"
$payloadPath = Join-Path $temporaryDirectory "event.json"
$responsePath = Join-Path $temporaryDirectory "response.json"

try {
    [IO.Directory]::CreateDirectory($temporaryDirectory) | Out-Null
    [IO.File]::WriteAllText($payloadPath, "{}", [Text.UTF8Encoding]::new($false))

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
        $errorBody = Get-Content -LiteralPath $responsePath -Raw
        throw "Lambda reported FunctionError: $errorBody"
    }

    if ($ExpectedVersion -and $metadata.ExecutedVersion -ne $ExpectedVersion) {
        throw (
            "Expected Lambda version $ExpectedVersion, " +
            "but executed version $($metadata.ExecutedVersion)."
        )
    }

    $observation = Get-Content -LiteralPath $responsePath -Raw | ConvertFrom-Json
    $expectedFields = @("checked_at", "service_name", "status")
    $actualFields = @($observation.PSObject.Properties.Name | Sort-Object)

    if (Compare-Object $expectedFields $actualFields) {
        throw "Unexpected observation fields: $($actualFields -join ', ')"
    }

    if (
        $observation.service_name -ne "service-sentinel-api" -or
        $observation.status -ne "HEALTHY" -or
        $observation.checked_at -le 0
    ) {
        throw "Unexpected monitor observation: $($observation | ConvertTo-Json -Compress)"
    }

    [pscustomobject]@{
        InvokeStatusCode = $metadata.StatusCode
        ExecutedVersion  = $metadata.ExecutedVersion
        Service          = $observation.service_name
        Status           = $observation.status
        CheckedAt        = $observation.checked_at
    }
}
finally {
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}
