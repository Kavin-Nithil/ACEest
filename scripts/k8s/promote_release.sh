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

PROMOTE_CANARY=${PROMOTE_CANARY:-true}

case "${DEPLOYMENT_STRATEGY}" in
    rolling)
        echo "Rolling deployment already promoted by Kubernetes."
        ;;
    blue-green)
        kubectl -n "${K8S_NAMESPACE}" patch service aceest-active --type merge \
            -p "{\"spec\":{\"selector\":{\"app\":\"aceest-fitness\",\"strategy\":\"blue-green\",\"color\":\"${CANDIDATE_COLOR}\"}}}"
        kubectl -n "${K8S_NAMESPACE}" patch service aceest-preview --type merge \
            -p "{\"spec\":{\"selector\":{\"app\":\"aceest-fitness\",\"strategy\":\"blue-green\",\"color\":\"${PREVIOUS_COLOR}\"}}}"
        echo "Blue-green cutover switched active traffic to ${CANDIDATE_COLOR}."
        ;;
    canary)
        if [[ "${PROMOTE_CANARY}" == "true" ]]; then
            kubectl -n "${K8S_NAMESPACE}" set image deployment/aceest-canary-stable aceest="${IMAGE}"
            kubectl -n "${K8S_NAMESPACE}" rollout status deployment/aceest-canary-stable --timeout=180s
            kubectl -n "${K8S_NAMESPACE}" delete ingress aceest-canary --ignore-not-found
            kubectl -n "${K8S_NAMESPACE}" scale deployment/aceest-canary-release --replicas=0
            echo "Canary image promoted to stable deployment."
        else
            echo "Canary release left running without promotion."
        fi
        ;;
    shadow)
        echo "Shadow deployment keeps stable traffic unchanged by design."
        ;;
    ab)
        echo "A/B deployment keeps variant B opt-in by header."
        ;;
    *)
        echo "Unsupported DEPLOYMENT_STRATEGY: ${DEPLOYMENT_STRATEGY}" >&2
        exit 1
        ;;
esac
