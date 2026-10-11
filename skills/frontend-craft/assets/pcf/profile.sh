#!/usr/bin/env bash
# .profile — runs in the app container after staging and before nginx starts (Cloud Foundry runs
# an app-root .profile for every app). Writes the runtime configuration the UI loads at startup from
# the environment the manifest or Apps Manager set, so one build serves every environment. Save this
# file as `.profile` at the deploy directory's root beside Staticfile. The staticfile buildpack
# serves $HOME/public, which is where the `root` directory was moved at staging. Never put a secret
# in these variables: the file reaches every browser.
set -Eeuo pipefail
shopt -s inherit_errexit

target="${HOME}/public/config.json"
: "${UI_ENVIRONMENT:?UI_ENVIRONMENT must be set (dev, staging, production ...)}"
: "${UI_API_BASE_URL:?UI_API_BASE_URL must be set (/v1 or an absolute https URL)}"

json_string() {
  # Escapes a value for a JSON string literal without needing jq in the container.
  local s=$1
  s=${s//\\/\\\\}; s=${s//\"/\\\"}; s=${s//$'\n'/\\n}; s=${s//$'\t'/\\t}
  printf '"%s"' "$s"
}

{
  printf '{\n'
  printf '  "environment": %s,\n' "$(json_string "$UI_ENVIRONMENT")"
  printf '  "apiBaseUrl": %s' "$(json_string "$UI_API_BASE_URL")"
  [[ -n "${UI_LOG_SEARCH_URL_TEMPLATE:-}" ]] && printf ',\n  "logSearchUrlTemplate": %s' "$(json_string "$UI_LOG_SEARCH_URL_TEMPLATE")"
  [[ -n "${UI_TRACE_URL_TEMPLATE:-}" ]] && printf ',\n  "traceUrlTemplate": %s' "$(json_string "$UI_TRACE_URL_TEMPLATE")"
  printf '\n}\n'
} > "${target}.tmp"
mv "${target}.tmp" "$target"
echo "wrote ${target} for environment ${UI_ENVIRONMENT}"
