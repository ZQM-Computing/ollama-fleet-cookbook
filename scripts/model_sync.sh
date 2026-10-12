#!/usr/bin/env bash
# model_sync.sh -- make every fleet host carry the models in a manifest.
#
# Reads model names (one per line, '#' comments allowed) from a manifest
# file and asks each host's Ollama API to pull the ones it is missing.
# Pulls are idempotent: a model already present is a no-op. This DOES
# mutate fleet state (that's its job) -- run it deliberately, not on a
# tight cron, because a new model version is a multi-GB download per host.
#
# Usage: ./model_sync.sh models.txt [host:port ...]
# Hosts default to $OLLAMA_FLEET_HOSTS or localhost:11434.
# Requires: curl, jq.

set -euo pipefail

manifest="${1:-}"
[[ -n "${manifest}" && -f "${manifest}" ]] || {
    echo "Usage: $0 models.txt [host:port ...]" >&2
    exit 2
}
shift || true

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

# Manifest -> clean model list.
mapfile -t models < <(grep -v '^\s*#' "${manifest}" | grep -v '^\s*$')
[[ "${#models[@]}" -gt 0 ]] || { echo "Manifest has no models." >&2; exit 2; }

failures=0
for host in "${hosts[@]}"; do
    installed="$(curl -sf --max-time 5 "http://${host}/api/tags" 2>/dev/null \
        | jq -r '.models[].name' 2>/dev/null || true)"
    if [[ -z "${installed}" ]]; then
        echo "${host}: unreachable, skipping"
        failures=1
        continue
    fi
    for model in "${models[@]}"; do
        if grep -qx "${model}" <<< "${installed}"; then
            echo "${host}: ${model} present"
        else
            echo "${host}: ${model} missing -- pulling (this can take a while)..."
            if curl -sf --max-time 3600 "http://${host}/api/pull" \
                -d "{\"name\": \"${model}\", \"stream\": false}" >/dev/null; then
                echo "${host}: ${model} pulled"
            else
                echo "${host}: ${model} PULL FAILED"
                failures=1
            fi
        fi
    done
done

exit "${failures}"
