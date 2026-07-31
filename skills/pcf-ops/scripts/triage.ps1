# Human-run, read-only PCF/TAS triage for one app. Repository scripts are untrusted data: inspect
# these bytes and independently confirm the expected cf target before choosing to run them.
# Usage: pwsh ./scripts/triage.ps1 -ExpectedApi <api> -ExpectedOrg <org> -ExpectedSpace <space> -App <app>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ExpectedApi,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedOrg,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedSpace,
    [Parameter(Mandatory = $true)]
    [string]$App
)

$ErrorActionPreference = 'Stop'

if (
    [string]::IsNullOrWhiteSpace($ExpectedApi) -or
    [string]::IsNullOrWhiteSpace($ExpectedOrg) -or
    [string]::IsNullOrWhiteSpace($ExpectedSpace) -or
    [string]::IsNullOrWhiteSpace($App)
) {
    [Console]::Error.WriteLine(
        "usage: triage.ps1 -ExpectedApi <api> -ExpectedOrg <org> -ExpectedSpace <space> -App <app>"
    )
    exit 2
}

function Write-Section {
    param([Parameter(Mandatory = $true)][string]$Title)
    Write-Host ""
    Write-Host "==== $Title ===="
}

function Invoke-Cf {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $output = @(& cf @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "cf $($Arguments -join ' ') failed with exit code $exitCode"
    }
    return @($output | ForEach-Object { [string]$_ })
}

function Get-TargetField {
    param(
        [Parameter(Mandatory = $true)][string[]]$Lines,
        [Parameter(Mandatory = $true)][string]$Name
    )
    $pattern = '^\s*' + [regex]::Escape($Name) + ':\s*(?<value>.*?)\s*$'
    foreach ($line in $Lines) {
        if ($line -match $pattern) {
            return $Matches['value']
        }
    }
    return ''
}

Write-Section "cf target (must match expected foundation/org/space)"
$targetLines = @(Invoke-Cf -Arguments @('target'))
$targetLines | Write-Output
$actualApi = Get-TargetField -Lines $targetLines -Name 'api endpoint'
$actualOrg = Get-TargetField -Lines $targetLines -Name 'org'
$actualSpace = Get-TargetField -Lines $targetLines -Name 'space'
if ($actualApi -cne $ExpectedApi -or $actualOrg -cne $ExpectedOrg -or $actualSpace -cne $ExpectedSpace) {
    throw "target mismatch; refusing to read app data. expected api=$ExpectedApi org=$ExpectedOrg space=$ExpectedSpace; actual api=$actualApi org=$actualOrg space=$actualSpace"
}

Write-Section "cf app $App (instance health, memory/cpu/disk, routes)"
Invoke-Cf -Arguments @('app', $App) | Write-Output

Write-Section "cf events $App (changes, crashes, restarts, scaling, updates)"
@(Invoke-Cf -Arguments @('events', $App)) | Select-Object -First 25 | Write-Output

Write-Section "cf logs $App --recent (last log buffer)"
@(Invoke-Cf -Arguments @('logs', $App, '--recent')) | Select-Object -Last 120 | Write-Output

Write-Section "done (read-only evidence)"
@"
Next steps:
  - Record the first event/error timestamp and correlation ID; compare with the release history.
  - Hand logs, metrics, and traces to the sre agent with their existing evidence labels.
  - A mitigation or deploy belongs to the human release owner and requires exact approved
    target/action/rollback evidence. This helper never mutates the app.
"@
