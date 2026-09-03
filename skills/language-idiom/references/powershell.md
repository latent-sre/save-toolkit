# PowerShell idiom

**Windows PowerShell 5.1** and **PowerShell 7+** differ — state which you target.

Defaults until the owner records a decision in stack-profile.

- **`[CmdletBinding()]`**, approved verbs (`Get-Verb`) with a singular noun, and
  `SupportsShouldProcess` on every state-changing function so `-WhatIf`/`-Confirm` work.
- **Emit objects** (`[pscustomobject]@{...}`) and let the caller format; never `Write-Host` for data
  — it bypasses the pipeline.
- **Pass `PSScriptAnalyzer`**, failing CI on `Error` severity, enforcing `PSUseApprovedVerbs`,
  `PSAvoidUsingCmdletAliases`, `PSUseShouldProcessForStateChangingFunctions`,
  `PSAvoidUsingInvokeExpression`, `PSAvoidUsingPlainTextForPassword`, and
  `PSAvoidUsingConvertToSecureStringWithPlainText`.
- **Pester 5** runs Discovery then Run — put setup in `BeforeAll`/`BeforeEach`, never bare code in
  `Describe`.
- **SecretManagement + SecretStore** for automation secrets at run time, and
  **`Set-AuthenticodeSignature`** on production scripts for hosts under `AllSigned` or Constrained
  Language Mode.
