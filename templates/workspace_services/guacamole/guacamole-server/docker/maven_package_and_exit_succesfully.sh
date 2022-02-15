#!/bin/bash

# 1. Remove any previously run failed flag
# 2. Run maven, but capture the exit code so we always succeed
# 3. Output a file if the tests are not successful.
rm -f /target/surefire-reports/guacamole_package_failed
pytest_result=$(mvn package)

if [ $? != 0 ]; then
  touch /target/surefire-reports/guacamole_package_failed
fi
