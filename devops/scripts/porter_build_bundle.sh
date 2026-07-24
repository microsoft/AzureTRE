#!/bin/bash

if [ -f "porter-build-context.env" ]; then

    # shellcheck disable=SC1091
    source "porter-build-context.env"

    echo "Found additional porter build context PORTER_BUILD_CONTEXT of $PORTER_BUILD_CONTEXT"

    # PORTER_BUILD_CONTEXT may declare more than one named build context,
    # separated by whitespace (e.g. "a=../x b=../y"). Pass each as its own
    # --build-context flag.
    build_context_args=()
    for context in $PORTER_BUILD_CONTEXT; do
        build_context_args+=(--build-context "$context")
    done
    porter build "${build_context_args[@]}"

else
    if [ -n "${CI_CACHE_ACR_FQDN}" ]; then

        # Ensure docker buildx builder exists with registry cache support
        if ! docker buildx inspect tre-builder >/dev/null 2>&1; then
            echo "Creating docker buildx builder with registry cache support..."
            docker buildx create --name tre-builder --driver docker-container --use
        else
            docker buildx use tre-builder
        fi

        ref="${CI_CACHE_ACR_FQDN}/build-cache/$(yq '.name' porter.yaml):porter"
        cache=(--cache-to "type=registry,ref=${ref},mode=max" --cache-from "type=registry,ref=${ref}")
    fi

    porter build "${cache[@]}"
fi
