#!/bin/bash

set -euo pipefail

# Always start fresh so downstream automation can detect the latest run.
rm -f /target/surefire-reports/guacamole_package_failed

# Build the extension even if tests later fail so the produced JAR contains
# the compiled classes and bundled resources Guacamole needs at runtime.
mvn -B -Dmaven.test.skip=true package

# Capture test failures without aborting the container build – the outer image
# still needs the freshly built artifacts when packaging fails.
if ! mvn -B test; then
  touch /target/surefire-reports/guacamole_package_failed
fi
