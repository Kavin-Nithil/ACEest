#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
STATE_FILE="${ROOT_DIR}/.deployment-state"

if [[ ! -f "${STATE_FILE}" ]]; then
    echo "No deployment state file found. Nothing to roll back."
    exit 0
fi

# shellcheck disable=SC1090
source "${STATE_FILE}"

case "${DEPLOYMENT_STRATEGY}" in
    rolling)
        kubectl -n "${K8S_NAMESPACE}" rollout undo deployment/aceest-rolling || true
        ;;
    blue-green)
        if [[ -n "${PREVIOUS_COLOR:-}" ]]; then
            kubectl -n "${K8S_NAMESPACE}" patch service aceest-active --type merge \
                -p "{\"spec\":{\"selector\":{\"app\":\"aceest-fitness\",\"strategy\":\"blue-green\",\"color\":\"${PREVIOUS_COLOR}\"}}}" || true
            if [[ -n "${CANDIDATE_COLOR:-}" ]]; then
                kubectl -n "${K8S_NAMESPACE}" patch service aceest-preview --type merge \
                    -p "{\"spec\":{\"selector\":{\"app\":\"aceest-fitness\",\"strategy\":\"blue-green\",\"color\":\"${CANDIDATE_COLOR}\"}}}" || true
            fi
        fi
        ;;
    canary)
        if [[ -n "${STABLE_IMAGE:-}" ]]; then
            kubectl -n "${K8S_NAMESPACE}" set image deployment/aceest-canary-stable aceest="${STABLE_IMAGE}" || true
        fi
        kubectl -n "${K8S_NAMESPACE}" delete ingress aceest-canary --ignore-not-found || true
        kubectl -n "${K8S_NAMESPACE}" scale deployment/aceest-canary-release --replicas=0 || true
        ;;
    shadow)
        kubectl -n "${K8S_NAMESPACE}" scale deployment/aceest-shadow-candidate --replicas=0 || true
        ;;
    ab)
        kubectl -n "${K8S_NAMESPACE}" delete ingress aceest-ab-experiment --ignore-not-found || true
        kubectl -n "${K8S_NAMESPACE}" scale deployment/aceest-ab-b --replicas=0 || true
        ;;
    *)
        echo "Unsupported DEPLOYMENT_STRATEGY: ${DEPLOYMENT_STRATEGY}" >&2
        exit 1
        ;;
esac

echo "Rollback completed for ${DEPLOYMENT_STRATEGY}"
