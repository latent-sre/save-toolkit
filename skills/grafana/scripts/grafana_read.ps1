# Query-only adapter for Windows PowerShell 5.1 and PowerShell 7.
# Script parameter binding preserves quotes; only base64 crosses the native argv boundary.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Datasource,
    [Parameter(Mandatory = $true)][ValidateSet('prometheus', 'loki')][string]$Kind,
    [Parameter(Mandatory = $true)][string]$From,
    [Parameter(Mandatory = $true)][string]$To,
    [Parameter(Mandatory = $true)][string]$Expr
)

$ErrorActionPreference = 'Stop'
try {
    $utf8 = [Text.UTF8Encoding]::new($false, $true)
    $encodedExpression = [Convert]::ToBase64String($utf8.GetBytes($Expr))
    $helperPath = Join-Path $PSScriptRoot 'grafana_read.py'
    & python -I -S $helperPath query --datasource $Datasource --kind $Kind --from $From --to $To --expr-base64 $encodedExpression
    exit $LASTEXITCODE
}
catch {
    Write-Output '{"ok":false,"error":"helper_launch_failed"}'
    exit 2
}
