#!/bin/bash

# 1. Remove any previously run failed flag
# 2. Run pytest, but capture the exit code so we always succeed
# 3. Output a file if the tests are not successful.
rm -f ../test-results/pytest_api*
mkdir -p ../test-results

if ! pytest --junit-xml ../test-results/pytest_api_unit.xml --ignore e2e_tests; then
  touch ../test-results/pytest_api_unit_failed
fi
