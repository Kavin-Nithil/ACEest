#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
STATE_FILE="${ROOT_DIR}/.deployment-state"
K8S_DIR="${ROOT_DIR}/k8s"

NAMESPACE=${K8S_NAMESPACE:-aceest}
STRATEGY=${DEPLOYMENT_STRATEGY:-rolling}
IMAGE_REPO=${IMAGE_REPO:-aceest-fitness}
IMAGE_TAG=${IMAGE_TAG:-latest}
IMAGE="${IMAGE_REPO}:${IMAGE_TAG}"
CANARY_WEIGHT=${CANARY_WEIGHT:-20}
APP_HOST=${APP_HOST:-aceest.local}

render() {
    local file=$1
    local stable_image=${STABLE_IMAGE:-$IMAGE}
    local stable_version=${STABLE_VERSION:-$IMAGE_TAG}
    local blue_image=${BLUE_IMAGE:-$IMAGE}
    local blue_version=${BLUE_VERSION:-$IMAGE_TAG}
    local green_image=${GREEN_IMAGE:-$IMAGE}
    local green_version=${GREEN_VERSION:-$IMAGE_TAG}
    local active_color=${ACTIVE_COLOR:-blue}
    local preview_color=${PREVIEW_COLOR:-green}

    sed \
        -e "s|__NAMESPACE__|${NAMESPACE}|g" \
        -e "s|__IMAGE__|${IMAGE}|g" \
        -e "s|__APP_VERSION__|${IMAGE_TAG}|g" \
        -e "s|__STABLE_IMAGE__|${stable_image}|g" \
        -e "s|__STABLE_VERSION__|${stable_version}|g" \
        -e "s|__BLUE_IMAGE__|${blue_image}|g" \
        -e "s|__BLUE_VERSION__|${blue_version}|g" \
        -e "s|__GREEN_IMAGE__|${green_image}|g" \
        -e "s|__GREEN_VERSION__|${green_version}|g" \
        -e "s|__ACTIVE_COLOR__|${active_color}|g" \
        -e "s|__PREVIEW_COLOR__|${preview_color}|g" \
        -e "s|__CANARY_WEIGHT__|${CANARY_WEIGHT}|g" \
        -e "s|__APP_HOST__|${APP_HOST}|g" \
        "${file}"
}

apply_manifest() {
    local file=$1
    render "${file}" | kubectl apply -f -
}

current_image() {
    local deployment=$1
    kubectl -n "${NAMESPACE}" get deployment "${deployment}" \
        -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || true
}

write_state() {
    cat > "${STATE_FILE}" <<EOF
DEPLOYMENT_STRATEGY=${STRATEGY}
K8S_NAMESPACE=${NAMESPACE}
APP_HOST=${APP_HOST}
IMAGE=${IMAGE}
IMAGE_TAG=${IMAGE_TAG}
STABLE_IMAGE=${STABLE_IMAGE:-}
STABLE_VERSION=${STABLE_VERSION:-}
PREVIOUS_COLOR=${PREVIOUS_COLOR:-}
CANDIDATE_COLOR=${CANDIDATE_COLOR:-}
EOF
}

apply_common() {
    apply_manifest "${K8S_DIR}/namespace.yaml"
    apply_manifest "${K8S_DIR}/configmap.yaml"
}

apply_common
rm -f "${STATE_FILE}"

case "${STRATEGY}" in
    rolling)
        apply_manifest "${K8S_DIR}/rolling/deployment.yaml"
        apply_manifest "${K8S_DIR}/rolling/service.yaml"
        write_state
        ;;
    blue-green)
        PREVIOUS_COLOR=$(kubectl -n "${NAMESPACE}" get service aceest-active \
            -o jsonpath='{.spec.selector.color}' 2>/dev/null || true)
        if [[ "${PREVIOUS_COLOR}" != "green" ]]; then
            PREVIOUS_COLOR=blue
            CANDIDATE_COLOR=green
        else
            CANDIDATE_COLOR=blue
        fi

        STABLE_IMAGE=$(current_image "aceest-${PREVIOUS_COLOR}")
        STABLE_VERSION=${STABLE_IMAGE##*:}
        if [[ -z "${STABLE_IMAGE}" ]]; then
            STABLE_IMAGE=${IMAGE}
            STABLE_VERSION=${IMAGE_TAG}
        fi

        if [[ "${CANDIDATE_COLOR}" == "blue" ]]; then
            BLUE_IMAGE=${IMAGE}
            BLUE_VERSION=${IMAGE_TAG}
            GREEN_IMAGE=${STABLE_IMAGE}
            GREEN_VERSION=${STABLE_VERSION}
        else
            BLUE_IMAGE=${STABLE_IMAGE}
            BLUE_VERSION=${STABLE_VERSION}
            GREEN_IMAGE=${IMAGE}
            GREEN_VERSION=${IMAGE_TAG}
        fi

        ACTIVE_COLOR=${PREVIOUS_COLOR}
        PREVIEW_COLOR=${CANDIDATE_COLOR}

        apply_manifest "${K8S_DIR}/blue-green/deployment-blue.yaml"
        apply_manifest "${K8S_DIR}/blue-green/deployment-green.yaml"
        apply_manifest "${K8S_DIR}/blue-green/service-active.yaml"
        apply_manifest "${K8S_DIR}/blue-green/service-preview.yaml"
        write_state
        ;;
    canary)
        STABLE_IMAGE=$(current_image "aceest-canary-stable")
        STABLE_VERSION=${STABLE_IMAGE##*:}
        if [[ -z "${STABLE_IMAGE}" ]]; then
            STABLE_IMAGE=${IMAGE}
            STABLE_VERSION=${IMAGE_TAG}
        fi

        apply_manifest "${K8S_DIR}/canary/deployment-stable.yaml"
        apply_manifest "${K8S_DIR}/canary/deployment-canary.yaml"
        apply_manifest "${K8S_DIR}/canary/service-stable.yaml"
        apply_manifest "${K8S_DIR}/canary/service-canary.yaml"
        apply_manifest "${K8S_DIR}/canary/ingress-stable.yaml"
        apply_manifest "${K8S_DIR}/canary/ingress-canary.yaml"
        write_state
        ;;
    shadow)
        STABLE_IMAGE=$(current_image "aceest-shadow-stable")
        STABLE_VERSION=${STABLE_IMAGE##*:}
        if [[ -z "${STABLE_IMAGE}" ]]; then
            STABLE_IMAGE=${IMAGE}
            STABLE_VERSION=${IMAGE_TAG}
        fi

        apply_manifest "${K8S_DIR}/shadow/deployment-stable.yaml"
        apply_manifest "${K8S_DIR}/shadow/deployment-shadow.yaml"
        apply_manifest "${K8S_DIR}/shadow/service-stable.yaml"
        apply_manifest "${K8S_DIR}/shadow/service-shadow.yaml"
        apply_manifest "${K8S_DIR}/shadow/ingress-mirror.yaml"
        write_state
        ;;
    ab)
        STABLE_IMAGE=$(current_image "aceest-ab-a")
        STABLE_VERSION=${STABLE_IMAGE##*:}
        if [[ -z "${STABLE_IMAGE}" ]]; then
            STABLE_IMAGE=${IMAGE}
            STABLE_VERSION=${IMAGE_TAG}
        fi

        apply_manifest "${K8S_DIR}/ab-testing/deployment-a.yaml"
        apply_manifest "${K8S_DIR}/ab-testing/deployment-b.yaml"
        apply_manifest "${K8S_DIR}/ab-testing/service-a.yaml"
        apply_manifest "${K8S_DIR}/ab-testing/service-b.yaml"
        apply_manifest "${K8S_DIR}/ab-testing/ingress-primary.yaml"
        apply_manifest "${K8S_DIR}/ab-testing/ingress-experiment.yaml"
        write_state
        ;;
    *)
        echo "Unsupported DEPLOYMENT_STRATEGY: ${STRATEGY}" >&2
        exit 1
        ;;
esac

echo "Applied ${STRATEGY} manifests for ${IMAGE} in namespace ${NAMESPACE}"
