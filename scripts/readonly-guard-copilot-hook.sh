#!/bin/sh
# Agent-scoped VS Code launcher; never register this globally.
IN=$(cat)
GUARD_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
G="$GUARD_DIR/readonly-guard.py"
for C in python3 python py; do
  command -v "$C" >/dev/null 2>&1 || continue
  OUT=$(printf '%s' "$IN" | "$C" -I -S "$G" --copilot 2>/dev/null); RC=$?
  if [ "$RC" -eq 42 ]; then exit 0; fi
  if [ "$RC" -eq 43 ] && [ -n "$OUT" ]; then printf '%s' "$OUT"; exit 0; fi
done
printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Save Toolkit command guard unavailable: no interpreter answered with the guard protocol. Repair the installed Python/guard before using SRE terminal reads."}}'
exit 0
