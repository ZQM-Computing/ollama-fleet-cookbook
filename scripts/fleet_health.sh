#!/usr/bin/env bash
# fleet_health.sh -- read-only health check across an Ollama fleet.
#
# For each host: is the API up (/api/tags), and what is loaded right now
# (/api/ps)? Exits 0 only if every host answers. Built for cron/monitoring
# wrappers and for the "is the fleet actually up?" moment before a demo.
#
# Hosts: pass as arguments, or set OLLAMA_FLEET_HOSTS (comma-separated
# host:port list). Default: localhost:11434.
#
# Usage: ./fleet_health.sh [host:port ...]
# Requires: curl, jq.

set -euo pipefail

for cmd in curl jq; do
    command -v "${cmd}" >/dev/null 2>&1 || {
        echo "ERROR: '${cmd}' is required." >&2
        exit 2
    }
done

if [[ "$#" -gt 0 ]]; then
    hosts=("$@")
elif [[ -n "${OLLAMA_FLEET_HOSTS:-}" ]]; then
    IFS=',' read -r -a hosts <<< "${OLLAMA_FLEET_HOSTS}"
else
    hosts=("localhost:11434")
fi

failures=0
for host in "${hosts[@]}"; do
    tags="$(curl -sf --max-time 5 "http://${host}/api/tags" 2>/dev/null || true)"
    if [[ -z "${tags}" ]]; then
        printf '%-22s DOWN (no answer on /api/tags)\n' "${host}"
        failures=1
        continue
    fi
    installed="$(jq -r '.models | length' <<< "${tags}")"
    loaded="$(curl -sf --max-time 5 "http://${host}/api/ps" 2>/dev/null \
        | jq -r '[.models[].name] | join(", ")' 2>/dev/null || echo '?')"
    printf '%-22s up   models installed: %-3s loaded: %s\n' \
        "${host}" "${installed}" "${loaded:-none}"
done

exit "${failures}"
