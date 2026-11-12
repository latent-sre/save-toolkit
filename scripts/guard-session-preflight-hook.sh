#!/bin/sh
# SessionStart launcher for the exact interpreter that must later run the Bash guard.
F="${CLAUDE_PLUGIN_ROOT}/scripts/guard-session-preflight.py"
TRACE=
REASON=
for C in python3 python py; do
  command -v "$C" >/dev/null 2>&1 || { TRACE="${TRACE}${C}=missing;"; continue; }
  OUT=$("$C" -I -S "$F" 2>/dev/null); RC=$?
  TRACE="${TRACE}${C}=exit-${RC};"
  if [ "$RC" -eq 42 ]; then exit 0; fi
  if [ "$RC" -eq 43 ] && [ -n "$OUT" ]; then REASON="$OUT"; fi
done
if [ -n "$REASON" ]; then printf '%s' "$REASON"; exit 0; fi
printf '%s' '{"systemMessage":"save-toolkit guard session preflight failed; candidate failures: '
printf '%s' "$TRACE"
printf '%s' '","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Guarded Bash remains fail-closed. Repair the lane PATH or plugin before relying on it."}}'
exit 0
