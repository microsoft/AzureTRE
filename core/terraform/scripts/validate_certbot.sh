#!/bin/bash

# Shared by the Make target and direct certificate-script invocation.
CERTBOT_BIN="${CERTBOT_BIN:-/opt/certbot/bin/certbot}"
if ! certbot_path=$(command -v -- "${CERTBOT_BIN}") || [[ ! -f "${certbot_path}" || ! -x "${certbot_path}" ]]; then
  printf "Certbot executable '%s' was not found or is not executable. Set CERTBOT_BIN to a valid executable path.\n" "${CERTBOT_BIN}" >&2
  exit 1
fi
