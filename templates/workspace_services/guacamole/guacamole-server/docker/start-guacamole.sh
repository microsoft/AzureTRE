#!/usr/bin/env bash
set -euo pipefail

log() {
  echo >&2 "$1"
}

shutdown_pending=0
tomcat_pid=""
guacd_pid=""
oauth_pid=""

terminate_processes() {
  local signal=${1:-TERM}
  shutdown_pending=1
  if [[ -n "$tomcat_pid" ]]; then
    kill "-$signal" "$tomcat_pid" 2>/dev/null || true
  fi
  if [[ -n "$guacd_pid" ]]; then
    kill "-$signal" "$guacd_pid" 2>/dev/null || true
  fi
  if [[ -n "$oauth_pid" ]]; then
    kill "-$signal" "$oauth_pid" 2>/dev/null || true
  fi
}

trap 'terminate_processes TERM' TERM
trap 'terminate_processes INT' INT

start_tomcat() {
  log "starting tomcat"
  if [[ -n "${APPLICATIONINSIGHTS_CONNECTION_STRING:-}" ]]; then
    export CATALINA_OPTS="${CATALINA_OPTS:-} -javaagent:/tmp/applicationinsights-agent.jar"
  else
    log "Application Insights disabled (missing APPLICATIONINSIGHTS_CONNECTION_STRING)"
  fi
  /usr/share/tomcat9/bin/catalina.sh run &
  tomcat_pid=$!
}

start_guacd() {
  log "starting guacd"
  /opt/guacamole/sbin/guacd -f -b 0.0.0.0 -L "${GUACD_LOG_LEVEL:-info}" -l 4822 &
  guacd_pid=$!
}

start_oauth() {
  local cookiesecret
  cookiesecret=$(dd if=/dev/urandom bs=32 count=1 2>/dev/null | base64 | tr -d '\n' | tr '+/' '-_')

  log "starting oauth2-proxy"
  set -x
  "${OAUTH2_PROXY_HOME}/oauth2-proxy" \
    --provider oidc \
    --skip-provider-button \
    --cookie-secret "${cookiesecret}" \
    --cookie-expire 0m \
    --oidc-issuer-url "${OAUTH2_PROXY_OIDC_ISSUER_URL}" \
    --upstream http://0.0.0.0:8080 \
    --email-domain "${OAUTH2_PROXY_EMAIL_DOMAIN}" \
    --redirect-url "${OAUTH2_PROXY_REDIRECT_URI}" --pass-host-header true \
    --show-debug-on-error true --pass-authorization-header true --pass-user-headers true \
    --http-address http://0.0.0.0:8085 \
    --https-address https://0.0.0.0:8086 \
    --cookie-secure true \
    --skip-claims-from-profile-url \
    --reverse-proxy true \
    --pass-access-token true \
    --set-xauthrequest true \
    --pass-basic-auth true \
    --cookie-refresh 50m \
    --insecure-oidc-allow-unverified-email true \
    --oidc-groups-claim "roles" \
    --oidc-email-claim "preferred_username" \
    --scope "openid offline_access ${AUDIENCE}/user_impersonation profile" &
  oauth_pid=$!
  set +x
}

start_tomcat
start_guacd
start_oauth

exited_service="unknown"
exit_code=0

while true; do
  if ! wait -n; then
    exit_code=$?
  else
    exit_code=0
  fi

  if [[ -n "$tomcat_pid" ]] && ! kill -0 "$tomcat_pid" 2>/dev/null; then
    if ! wait "$tomcat_pid" 2>/dev/null; then
      exit_code=$?
    fi
    exited_service="tomcat"
    break
  fi

  if [[ -n "$guacd_pid" ]] && ! kill -0 "$guacd_pid" 2>/dev/null; then
    if ! wait "$guacd_pid" 2>/dev/null; then
      exit_code=$?
    fi
    exited_service="guacd"
    break
  fi

  if [[ -n "$oauth_pid" ]] && ! kill -0 "$oauth_pid" 2>/dev/null; then
    if ! wait "$oauth_pid" 2>/dev/null; then
      exit_code=$?
    fi
    exited_service="oauth"
    break
  fi
done

log "${exited_service} exited. code=${exit_code}"

if [[ $shutdown_pending -eq 0 ]]; then
  terminate_processes TERM
fi

wait "$tomcat_pid" 2>/dev/null || true
wait "$guacd_pid" 2>/dev/null || true
wait "$oauth_pid" 2>/dev/null || true

exit "$exit_code"
