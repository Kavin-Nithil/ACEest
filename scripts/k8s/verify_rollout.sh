#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
STATE_FILE="${ROOT_DIR}/.deployment-state"

if [[ ! -f "${STATE_FILE}" ]]; then
    echo "Deployment state file is missing: ${STATE_FILE}" >&2
    exit 1
fi

# shellcheck disable=SC1090
source "${STATE_FILE}"

TMP_DIR=$(mktemp -d)
PF_PID=

cleanup() {
    if [[ -n "${PF_PID:-}" ]]; then
        kill "${PF_PID}" 2>/dev/null || true
        wait "${PF_PID}" 2>/dev/null || true
    fi
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

wait_for_port() {
    local port=$1
    for _ in $(seq 1 20); do
        if python3 - <<PY
import socket
s = socket.socket()
s.settimeout(0.2)
try:
    s.connect(("127.0.0.1", ${port}))
except OSError:
    raise SystemExit(1)
raise SystemExit(0)
PY
        then
            return 0
        fi
        sleep 1
    done
    return 1
}

start_port_forward() {
    local namespace=$1
    local resource=$2
    local local_port=$3
    local remote_port=$4

    kubectl -n "${namespace}" port-forward "${resource}" "${local_port}:${remote_port}" \
        > "${TMP_DIR}/port-forward.log" 2>&1 &
    PF_PID=$!
    wait_for_port "${local_port}"
}

assert_health_field() {
    local json_file=$1
    local field=$2
    local expected=$3

    python3 - "${json_file}" "${field}" "${expected}" <<'PY'
import json
import sys

path, field, expected = sys.argv[1:4]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

current = data
for part in field.split("."):
    current = current[part]

if str(current) != expected:
    raise SystemExit(f"{field} expected {expected!r} but got {current!r}")
PY
}

curl_health() {
    local url=$1
    shift
    curl --silent --show-error --fail "$@" "${url}/health"
}

case "${DEPLOYMENT_STRATEGY}" in
    rolling)
        kubectl -n "${K8S_NAMESPACE}" rollout status deployment/aceest-rolling --timeout=180s
        start_port_forward "${K8S_NAMESPACE}" service/aceest-rolling 18081 80
        curl_health "http://127.0.0.1:18081" > "${TMP_DIR}/rolling.json"
        assert_health_field "${TMP_DIR}/rolling.json" "status" "ok"
        assert_health_field "${TMP_DIR}/rolling.json" "deployment.version" "${IMAGE_TAG}"
        ;;
    blue-green)
        kubectl -n "${K8S_NAMESPACE}" rollout status "deployment/aceest-${CANDIDATE_COLOR}" --timeout=180s
        start_port_forward "${K8S_NAMESPACE}" service/aceest-preview 18082 80
        curl_health "http://127.0.0.1:18082" > "${TMP_DIR}/blue-green.json"
        assert_health_field "${TMP_DIR}/blue-green.json" "status" "ok"
        assert_health_field "${TMP_DIR}/blue-green.json" "deployment.color" "${CANDIDATE_COLOR}"
        assert_health_field "${TMP_DIR}/blue-green.json" "deployment.version" "${IMAGE_TAG}"
        ;;
    canary)
        kubectl -n "${K8S_NAMESPACE}" rollout status deployment/aceest-canary-stable --timeout=180s
        kubectl -n "${K8S_NAMESPACE}" rollout status deployment/aceest-canary-release --timeout=180s
        start_port_forward ingress-nginx service/ingress-nginx-controller 18080 80
        curl_health "http://127.0.0.1:18080" -H "Host: ${APP_HOST}" > "${TMP_DIR}/canary-stable.json"
        curl_health "http://127.0.0.1:18080" -H "Host: ${APP_HOST}" -H "X-Canary: always" > "${TMP_DIR}/canary-release.json"
        assert_health_field "${TMP_DIR}/canary-stable.json" "deployment.track" "stable"
        assert_health_field "${TMP_DIR}/canary-release.json" "deployment.track" "canary"
        assert_health_field "${TMP_DIR}/canary-release.json" "deployment.version" "${IMAGE_TAG}"
        ;;
    shadow)
        kubectl -n "${K8S_NAMESPACE}" rollout status deployment/aceest-shadow-stable --timeout=180s
        kubectl -n "${K8S_NAMESPACE}" rollout status deployment/aceest-shadow-candidate --timeout=180s
        start_port_forward ingress-nginx service/ingress-nginx-controller 18083 80
        curl_health "http://127.0.0.1:18083" -H "Host: ${APP_HOST}" > "${TMP_DIR}/shadow-stable.json"
        sleep 2
        kubectl -n "${K8S_NAMESPACE}" logs deployment/aceest-shadow-candidate --since=2m \
            > "${TMP_DIR}/shadow.logs"
        assert_health_field "${TMP_DIR}/shadow-stable.json" "deployment.track" "stable"
        grep -q "/health" "${TMP_DIR}/shadow.logs"
        ;;
    ab)
        kubectl -n "${K8S_NAMESPACE}" rollout status deployment/aceest-ab-a --timeout=180s
        kubectl -n "${K8S_NAMESPACE}" rollout status deployment/aceest-ab-b --timeout=180s
        start_port_forward ingress-nginx service/ingress-nginx-controller 18084 80
        curl_health "http://127.0.0.1:18084" -H "Host: ${APP_HOST}" > "${TMP_DIR}/ab-a.json"
        curl_health "http://127.0.0.1:18084" -H "Host: ${APP_HOST}" -H "X-Experiment: fitness-b" \
            > "${TMP_DIR}/ab-b.json"
        assert_health_field "${TMP_DIR}/ab-a.json" "deployment.experiment" "variant-a"
        assert_health_field "${TMP_DIR}/ab-b.json" "deployment.experiment" "variant-b"
        assert_health_field "${TMP_DIR}/ab-b.json" "deployment.version" "${IMAGE_TAG}"
        ;;
    *)
        echo "Unsupported DEPLOYMENT_STRATEGY: ${DEPLOYMENT_STRATEGY}" >&2
        exit 1
        ;;
esac

echo "Deployment verification passed for ${DEPLOYMENT_STRATEGY}"
