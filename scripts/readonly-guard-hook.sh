#!/bin/sh
# Fail-closed launcher for the read-only allowlist guard (scripts/readonly-guard.py).
# Wired session-wide from hooks/hooks.json because plugin-shipped agents ignore frontmatter hooks.
# Protocol: guard exits 42 = allow (empty stdout), 43 = deny (permissionDecision JSON on stdout).
# Every Bash payload reaches the Python parser. Raw-JSON shell prefilters are forbidden: harmless
# whitespace drift or an upstream identity-key rename would otherwise bypass the parser's canary.
# If NO interpreter answers with the guard's own exit codes, deny all Bash until the plugin is
# restored. That broken-dependency path is intentionally disruptive rather than silently unsafe.
IN=$(cat)
G="${CLAUDE_PLUGIN_ROOT}/scripts/readonly-guard.py"
for C in python3 python py; do
  command -v "$C" >/dev/null 2>&1 || continue
  OUT=$(printf '%s' "$IN" | "$C" -I -S "$G" 2>/dev/null); RC=$?
  if [ "$RC" -eq 42 ]; then exit 0; fi
  if [ "$RC" -eq 43 ]; then printf '%s' "$OUT"; exit 0; fi
done
printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"sre-agents read-only guard unavailable or failed: no interpreter answered with the guard exit codes (tried python3, python, py). All Bash is denied while this plugin is broken so a guarded agent cannot bypass its allowlist. Restore Python 3 or disable/reinstall the plugin."}}'
exit 0
