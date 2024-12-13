#!/bin/bash

if [ -f "porter-build-context.env" ]; then

    # shellcheck disable=SC1091
    source "porter-build-context.env"

    echo "Found additional porter build context PORTER_BUILD_CONTEXT of $PORTER_BUILD_CONTEXT"
    porter build --build-context "$PORTER_BUILD_CONTEXT"

else
    porter build
fi
