#!/bin/bash

DOCKER_DEVCONTAINER_BUILD_CONTEXT_ARGS=()
docker_devcontainer_ca_dockerfile=""
docker_devcontainer_ca_dockerfile_backup=""
docker_devcontainer_ca_dockerfile_backup_ready=false
docker_devcontainer_ca_context_dir=""

docker_devcontainer_ca_restore() {
    if [ -n "${docker_devcontainer_ca_dockerfile_backup}" ] && [ -f "${docker_devcontainer_ca_dockerfile_backup}" ]; then
        if [ "${docker_devcontainer_ca_dockerfile_backup_ready}" = "true" ]; then
            cp -p -- "${docker_devcontainer_ca_dockerfile_backup}" "${docker_devcontainer_ca_dockerfile}"
        fi
        rm -f -- "${docker_devcontainer_ca_dockerfile_backup}"
    fi

    if [ -n "${docker_devcontainer_ca_context_dir}" ] && [ -d "${docker_devcontainer_ca_context_dir}" ]; then
        rm -rf -- "${docker_devcontainer_ca_context_dir}"
    fi

    DOCKER_DEVCONTAINER_BUILD_CONTEXT_ARGS=()
    docker_devcontainer_ca_dockerfile=""
    docker_devcontainer_ca_dockerfile_backup=""
    docker_devcontainer_ca_dockerfile_backup_ready=false
    docker_devcontainer_ca_context_dir=""
    trap - EXIT HUP INT TERM
}

docker_devcontainer_ca_patch() {
    if [ "${DEVCONTAINER:-}" != "true" ]; then
        return 0
    fi

    if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
        echo "Unable to find Dockerfile ${1:-}" >&2
        return 1
    fi

    local helper_dir trusted_ca_source
    helper_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    trusted_ca_source="$(cd "${helper_dir}/../.." && pwd)/.devcontainer/trusted_ca"
    docker_devcontainer_ca_dockerfile="$1"

    if [ ! -d "${trusted_ca_source}" ]; then
        echo "Unable to find trusted CA directory ${trusted_ca_source}" >&2
        return 1
    fi

    if ! find "${trusted_ca_source}" -maxdepth 1 -type f \( -name '*.crt' -o -name '*.pem' -o -name '*.cer' \) -print -quit | grep -q .; then
        echo "No .crt, .pem, or .cer files found in ${trusted_ca_source}" >&2
        return 1
    fi

    docker_devcontainer_ca_context_dir=$(mktemp -d) || return 1
    docker_devcontainer_ca_dockerfile_backup=$(mktemp) || {
        docker_devcontainer_ca_restore
        return 1
    }
    trap docker_devcontainer_ca_restore EXIT HUP INT TERM

    if ! cp -p -- "${docker_devcontainer_ca_dockerfile}" "${docker_devcontainer_ca_dockerfile_backup}"; then
        docker_devcontainer_ca_restore
        return 1
    fi
    docker_devcontainer_ca_dockerfile_backup_ready=true

    if ! find "${trusted_ca_source}" -maxdepth 1 -type f \( -name '*.crt' -o -name '*.pem' -o -name '*.cer' \) -exec cp -- {} "${docker_devcontainer_ca_context_dir}" \;; then
        docker_devcontainer_ca_restore
        return 1
    fi
    DOCKER_DEVCONTAINER_BUILD_CONTEXT_ARGS=(--build-context "devcontainer-trusted-ca=${docker_devcontainer_ca_context_dir}")

    if ! awk '
        function emit_setup() {
            print ""
            print "COPY --from=devcontainer-trusted-ca . /tmp/devcontainer-trusted-ca/"
            print "RUN { if [ -f /etc/ssl/certs/ca-certificates.crt ]; then cat /etc/ssl/certs/ca-certificates.crt; fi; for cert in /tmp/devcontainer-trusted-ca/*; do cat \"$cert\"; echo; done; } > /tmp/devcontainer-ca-certificates.crt && mkdir -p /usr/local/share/ca-certificates && for cert in /tmp/devcontainer-trusted-ca/*; do cert_name=$(basename \"$cert\"); cp \"$cert\" \"/usr/local/share/ca-certificates/azuretre-devcontainer-${cert_name}.crt\"; done && if command -v update-ca-certificates >/dev/null 2>&1; then update-ca-certificates; fi"
            print "RUN if command -v keytool >/dev/null 2>&1; then if [ -n \"${JAVA_HOME:-}\" ] && [ -f \"${JAVA_HOME}/lib/security/cacerts\" ]; then cp \"${JAVA_HOME}/lib/security/cacerts\" /tmp/devcontainer-java-cacerts; fi; for cert in /tmp/devcontainer-trusted-ca/*; do cert_name=$(basename \"$cert\"); keytool -importcert -noprompt -alias \"azuretre-devcontainer-${cert_name}\" -file \"$cert\" -keystore /tmp/devcontainer-java-cacerts -storepass changeit; done; fi"
            print "ARG SSL_CERT_FILE=/tmp/devcontainer-ca-certificates.crt"
            print "ARG CURL_CA_BUNDLE=/tmp/devcontainer-ca-certificates.crt"
            print "ARG MAVEN_OPTS=\"-Djavax.net.ssl.trustStore=/tmp/devcontainer-java-cacerts -Djavax.net.ssl.trustStorePassword=changeit\""
            print "ARG NODE_EXTRA_CA_CERTS=/tmp/devcontainer-ca-certificates.crt"
        }
        function emit_cleanup(final_user) {
            print ""
            if (final_user != "") print "USER root"
            print "RUN for cert in /tmp/devcontainer-trusted-ca/*; do cert_name=$(basename \"$cert\"); rm -f \"/usr/local/share/ca-certificates/azuretre-devcontainer-${cert_name}.crt\"; done && if command -v update-ca-certificates >/dev/null 2>&1; then update-ca-certificates; fi && rm -rf /tmp/devcontainer-trusted-ca /tmp/devcontainer-ca-certificates.crt /tmp/devcontainer-java-cacerts"
            if (final_user != "") print final_user
        }
        function flush_stage(    i, root_user_line, final_user, is_scratch) {
            split(stage[1], from_fields, /[[:space:]]+/)
            is_scratch = (tolower(from_fields[2]) == "scratch")
            root_user_line = 0
            final_user = ""

            for (i = 1; i <= stage_line_count; i++) {
                if (root_user_line == 0 && stage[i] ~ /^USER[[:space:]]+root([[:space:]:]|$)/) root_user_line = i
                if (stage[i] ~ /^USER([[:space:]]|$)/) final_user = stage[i]
            }

            for (i = 1; i <= stage_line_count; i++) {
                print stage[i]
                if (!is_scratch && ((root_user_line == 0 && i == 1) || i == root_user_line)) emit_setup()
                delete stage[i]
            }

            if (!is_scratch) emit_cleanup(final_user)
            stage_line_count = 0
        }
        /^FROM([[:space:]]|$)/ {
            if (seen_stage) flush_stage()
            seen_stage = 1
            stage[++stage_line_count] = $0
            next
        }
        !seen_stage { print; next }
        { stage[++stage_line_count] = $0 }
        END {
            if (!seen_stage) exit 1
            flush_stage()
        }
    ' "${docker_devcontainer_ca_dockerfile_backup}" > "${docker_devcontainer_ca_dockerfile}"; then
        docker_devcontainer_ca_restore
        return 1
    fi
}
