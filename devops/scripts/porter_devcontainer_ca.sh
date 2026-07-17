#!/bin/bash

PORTER_DEVCONTAINER_BUILD_CONTEXT_ARGS=()
porter_devcontainer_ca_dockerfile=""
porter_devcontainer_ca_dockerfile_backup=""
porter_devcontainer_ca_dockerfile_backup_ready=false
porter_devcontainer_ca_context_dir=""

porter_devcontainer_ca_restore() {
    if [ -n "${porter_devcontainer_ca_dockerfile_backup}" ] && [ -f "${porter_devcontainer_ca_dockerfile_backup}" ]; then
        if [ "${porter_devcontainer_ca_dockerfile_backup_ready}" = "true" ]; then
            cp -p -- "${porter_devcontainer_ca_dockerfile_backup}" "${porter_devcontainer_ca_dockerfile}"
        fi
        rm -f -- "${porter_devcontainer_ca_dockerfile_backup}"
    fi

    if [ -n "${porter_devcontainer_ca_context_dir}" ] && [ -d "${porter_devcontainer_ca_context_dir}" ]; then
        rm -rf -- "${porter_devcontainer_ca_context_dir}"
    fi

    PORTER_DEVCONTAINER_BUILD_CONTEXT_ARGS=()
    porter_devcontainer_ca_dockerfile=""
    porter_devcontainer_ca_dockerfile_backup=""
    porter_devcontainer_ca_dockerfile_backup_ready=false
    porter_devcontainer_ca_context_dir=""
    trap - EXIT HUP INT TERM
}

porter_devcontainer_ca_patch() {
    if [ "${DEVCONTAINER:-}" != "true" ]; then
        return 0
    fi

    local helper_dir trusted_ca_source
    helper_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    trusted_ca_source="$(cd "${helper_dir}/../.." && pwd)/.devcontainer/trusted_ca"
    porter_devcontainer_ca_dockerfile=$(yq eval -r '.dockerfile // ""' porter.yaml)

    if [ -z "${porter_devcontainer_ca_dockerfile}" ] || [ ! -f "${porter_devcontainer_ca_dockerfile}" ]; then
        echo "Unable to find the Dockerfile template configured in porter.yaml" >&2
        return 1
    fi

    if ! grep -q '^# PORTER_INIT$' "${porter_devcontainer_ca_dockerfile}"; then
        echo "Unable to find the # PORTER_INIT marker in ${porter_devcontainer_ca_dockerfile}" >&2
        return 1
    fi

    if [ ! -d "${trusted_ca_source}" ]; then
        echo "Unable to find trusted CA directory ${trusted_ca_source}" >&2
        return 1
    fi

    if ! find "${trusted_ca_source}" -maxdepth 1 -type f \( -name '*.crt' -o -name '*.pem' -o -name '*.cer' \) -print -quit | grep -q .; then
        echo "No .crt, .pem, or .cer files found in ${trusted_ca_source}" >&2
        return 1
    fi

    porter_devcontainer_ca_context_dir=$(mktemp -d) || return 1
    porter_devcontainer_ca_dockerfile_backup=$(mktemp) || {
        porter_devcontainer_ca_restore
        return 1
    }
    trap porter_devcontainer_ca_restore EXIT HUP INT TERM

    if ! cp -p -- "${porter_devcontainer_ca_dockerfile}" "${porter_devcontainer_ca_dockerfile_backup}"; then
        porter_devcontainer_ca_restore
        return 1
    fi
    porter_devcontainer_ca_dockerfile_backup_ready=true

    if ! find "${trusted_ca_source}" -maxdepth 1 -type f \( -name '*.crt' -o -name '*.pem' -o -name '*.cer' \) -exec cp -- {} "${porter_devcontainer_ca_context_dir}" \;; then
        porter_devcontainer_ca_restore
        return 1
    fi
    PORTER_DEVCONTAINER_BUILD_CONTEXT_ARGS=(--build-context "devcontainer-trusted-ca=${porter_devcontainer_ca_context_dir}")

    if ! awk '
        /^# PORTER_INIT$/ {
            print "COPY --from=devcontainer-trusted-ca . /tmp/devcontainer-trusted-ca/"
            print "RUN mkdir -p /usr/local/share/ca-certificates && for cert in /tmp/devcontainer-trusted-ca/*; do cert_name=$(basename \"$cert\"); cp \"$cert\" \"/usr/local/share/ca-certificates/azuretre-devcontainer-${cert_name}.crt\"; done && if command -v update-ca-certificates >/dev/null 2>&1; then update-ca-certificates; fi"
            print "ARG SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt"
            print "ARG CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt"
            print "ARG NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt"
            print ""
        }
        { print }
        END {
            print ""
            print "RUN for cert in /tmp/devcontainer-trusted-ca/*; do cert_name=$(basename \"$cert\"); rm -f \"/usr/local/share/ca-certificates/azuretre-devcontainer-${cert_name}.crt\"; done && rm -rf /tmp/devcontainer-trusted-ca && if command -v update-ca-certificates >/dev/null 2>&1; then update-ca-certificates; fi"
        }
    ' "${porter_devcontainer_ca_dockerfile_backup}" > "${porter_devcontainer_ca_dockerfile}"; then
        porter_devcontainer_ca_restore
        return 1
    fi
}
