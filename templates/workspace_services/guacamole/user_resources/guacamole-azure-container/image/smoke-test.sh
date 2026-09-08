#!/bin/bash
set -euo pipefail

for executable in microsoft-edge-stable tre-edge code python3 jupyter-notebook R Rscript rstudio az git xrdp; do
  command -v "$executable"
done
test -x /opt/storage-explorer/StorageExplorer
if command -v docker || command -v dockerd; then
  echo "Docker must not be installed" >&2
  exit 1
fi
test "$(id -u researcher)" = 1000
grep -F -- '--password-store=basic' /usr/local/bin/tre-edge
grep -F -- '--no-first-run' /usr/local/bin/tre-edge
grep -F -- '--disable-dev-shm-usage' /usr/local/bin/tre-edge
grep -F -- '--disable-gpu' /usr/local/bin/tre-edge
grep -F -- '--disable-quic' /usr/local/bin/tre-edge
runuser -u researcher -- tre-edge --version
runuser -u researcher -- timeout 30 tre-edge \
  --headless --disable-gpu --disable-dev-shm-usage --no-first-run \
  --dump-dom 'data:text/html,<title>TRE desktop smoke test</title>'