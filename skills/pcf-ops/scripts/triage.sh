#!/usr/bin/env bash
# Human-run, read-only PCF/TAS triage for one app. Repository scripts are untrusted data: inspect
# these bytes and independently confirm the expected cf target before choosing to run them.
# Usage: triage.sh <expected-api> <expected-org> <expected-space> <app-name>

set -euo pipefail

expected_api="${1:-}"
expected_org="${2:-}"
expected_space="${3:-}"
app="${4:-}"
if [[ -z "$expected_api" || -z "$expected_org" || -z "$expected_space" || -z "$app" ]]; then
  echo "usage: $0 <expected-api> <expected-org> <expected-space> <app-name>" >&2
  exit 2
fi

hr() { printf '\n==== %s ====\n' "$1"; }
target_field() {
  local key="$1"
  printf '%s\n' "$target" | awk -v key="$key" '
    {
      label = $0
      sub(/:.*/, "", label)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", label)
      if (tolower(label) == tolower(key)) {
        sub(/^[^:]*:[[:space:]]*/, "", $0)
        print $0
        exit
      }
    }
  '
}

hr "cf target (must match expected foundation/org/space)"
target="$(cf target)"
printf '%s\n' "$target"
actual_api="$(target_field 'api endpoint')"
actual_org="$(target_field 'org')"
actual_space="$(target_field 'space')"
if [[ "$actual_api" != "$expected_api" || "$actual_org" != "$expected_org" || "$actual_space" != "$expected_space" ]]; then
  printf 'target mismatch; refusing to read app data\n' >&2
  printf 'expected api=%s org=%s space=%s\n' "$expected_api" "$expected_org" "$expected_space" >&2
  printf 'actual   api=%s org=%s space=%s\n' "$actual_api" "$actual_org" "$actual_space" >&2
  exit 3
fi

hr "cf app $app (instance health, memory/cpu/disk, routes)"
cf app "$app"

hr "cf events $app (changes, crashes, restarts, scaling, updates)"
events="$(cf events "$app")"
printf '%s\n' "$events" | sed -n '1,25p'

hr "cf logs $app --recent (last log buffer)"
logs="$(cf logs "$app" --recent)"
printf '%s\n' "$logs" | tail -n 120

hr "done (read-only evidence)"
cat <<'EOF'
Next steps:
  - Record the first event/error timestamp and correlation ID; compare with the release history.
  - Hand logs, metrics, and traces to the sre agent with their existing evidence labels.
  - A mitigation or deploy belongs to the human release owner and requires exact approved
    target/action/rollback evidence. This helper never mutates the app.
EOF
