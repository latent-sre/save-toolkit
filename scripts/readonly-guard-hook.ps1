param([switch]$Copilot)

# Translate the guard's authenticated 42/43/44 protocol into a host permission decision.
# The Copilot switch is for the SRE agent-scoped hook only, never a session-wide hook.
$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$guardInput = [Console]::In.ReadToEnd()
$guardPath = Join-Path $PSScriptRoot 'readonly-guard.py'
$guardArgs = @()
if ($Copilot) { $guardArgs = @('--copilot') }
foreach ($candidate in @('python3', 'python', 'py')) {
    try {
        $interpreter = Get-Command $candidate -CommandType Application -ErrorAction Stop | Select-Object -First 1
        $guardOutput = $guardInput | & $interpreter.Source -I -S $guardPath @guardArgs 2>$null
        $guardExit = $LASTEXITCODE
        if ($guardExit -eq 42) { exit 0 }
        if ($guardExit -eq 43 -and -not [string]::IsNullOrWhiteSpace(($guardOutput -join "`n"))) {
            [Console]::Out.WriteLine(($guardOutput -join "`n"))
            exit 0
        }
    } catch {
        # A missing/stub interpreter is not an allow decision. Try the next candidate.
    }
}
[Console]::Out.WriteLine('{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Save Toolkit command guard unavailable: no interpreter answered with the guard protocol. Repair the installed Python/guard before using SRE terminal reads."}}')
exit 0
