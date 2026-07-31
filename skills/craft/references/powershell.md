# PowerShell craft

Write cmdlet-style PowerShell that composes in a pipeline and fails safely. **Windows PowerShell 5.1**
and **PowerShell 7+** differ — state which you target.

## Function shape
```powershell
function Get-Thing {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Name,
        [int]$Count = 1
    )
    # comment-based help above; approved verb (Get/Set/New/Remove/...) + singular noun
}
```
- **Approved verbs** (`Get-Verb`); `[CmdletBinding()]` + typed, validated params
  (`[ValidateSet()]`, `[ValidateNotNullOrEmpty()]`).
- Support `-WhatIf`/`-Confirm` via `SupportsShouldProcess` for state-changing functions.

## Error handling
- Set `$ErrorActionPreference = 'Stop'` (or `-ErrorAction Stop` per call) so failures are catchable;
  wrap risky work in `try/catch`. Don't rely on `$?`.
- Throw `terminating` errors for real failures; use `Write-Error` for non-terminating with context.
- In a `catch`, re-throw with `$PSCmdlet.ThrowTerminatingError($PSItem)` (keeps your cmdlet as the
  error source — better than a bare `throw`).

## Output & pipeline
- **Emit objects, not formatted text** (`[pscustomobject]@{...}`); let the caller format. Reserve
  `Format-*` for the end of a display pipeline.
- **Never `Write-Host` for data** — it bypasses the pipeline. Use `Write-Output`/return, and
  `Write-Verbose`/`Write-Information` for diagnostics.

## Correctness traps
- **`$null` on the left:** `if ($null -eq $x)`, not `if ($x -eq $null)` (array-comparison gotcha).
- Use **splatting** for many params: `$p = @{ Name='x'; Count=2 }; Get-Thing @p`.
- `5.1 vs 7`: `??`/`?:`/ternary, `ForEach-Object -Parallel`, and some cmdlets are 7-only. Avoid
  `2>&1` capture quirks on native exes in 5.1.
- Need a Windows-PowerShell-only module from PS 7? `Import-Module <name> -UseWindowsPowerShell` proxies
  via a 5.1 session — but objects return **deserialized** (properties only, no live methods).

## Cross-platform (PS 7 on Linux/PCF too)
- Don't hardcode separators: use `Join-Path` and `[IO.Path]::DirectorySeparatorChar` for paths,
  `[IO.Path]::PathSeparator` for PATH-style lists.
- Branch OS-specific work on the automatic vars `$IsWindows` / `$IsLinux` / `$IsMacOS`.
- Linux is **case-sensitive** for both file paths *and* environment-variable names (`$env:Path` ≠
  `$env:PATH`) — match exact case.

## Secrets & signing
- Pull automation secrets from a vault at run time via **SecretManagement + SecretStore** (or Azure Key
  Vault / HashiCorp Vault) — `Get-Secret` — never bake them into scripts, params, or transcripts.
- Sign production scripts with **`Set-AuthenticodeSignature`** so they run under `AllSigned` policy /
  Constrained Language Mode on locked-down hosts.

## Quality gate & tests
- **Pass `PSScriptAnalyzer`** (fail CI on `Error` severity). High-value rules to enforce:
  `PSUseApprovedVerbs`, `PSAvoidUsingCmdletAliases`, `PSUseShouldProcessForStateChangingFunctions`,
  `PSAvoidUsingInvokeExpression`, `PSAvoidUsingPlainTextForPassword`,
  `PSAvoidUsingConvertToSecureStringWithPlainText`.
- Test with **`Pester`**: `Describe/Context/It`, `Mock`, `Should`; test param validation and error paths.
  **Pester 5** runs Discovery then Run — put setup in `BeforeAll`/`BeforeEach` (not bare code in
  `Describe`), share state via `$script:`, assert mocks with `Should -Invoke`. See the [tests-first process](./tdd.md).
- Keep secrets out of logs/transcripts; use `SecureString`/credential objects, never plaintext.
