# The test validates SERVER, VAULT_NAME, SECRET_NAME, DATABASE, PROBE_ID and PHASE and sets them above this line.
set -euo pipefail
stage=input
fail() {
  # Do not print command output, tokens or the password.
  echo "MYSQL_PROBE_FAILED=$stage"
  exit 1
}
[[ "$SERVER" =~ ^[a-z0-9-]+\.mysql\.database\.azure\.com$ ]] || fail
[[ "$VAULT_NAME" =~ ^[a-z0-9-]+$ ]] || fail
[[ "$SECRET_NAME" =~ ^[a-z0-9-]+$ ]] || fail
[[ "$DATABASE" =~ ^[a-z0-9_]+$ ]] || fail
[[ "$PROBE_ID" =~ ^[a-f0-9]{32}$ ]] || fail
[[ "$PHASE" =~ ^(write|read)$ ]] || fail

stage=private-dns
addresses=$(getent ahostsv4 "$SERVER" | awk '{print $1}' | sort -u) || fail
[ -n "$addresses" ] || fail
for address in $addresses; do
  case "$address" in
    10.* | 192.168.* | 172.1[6-9].* | 172.2[0-9].* | 172.3[01].*) ;;
    *) fail ;;
  esac
done

stage=mysql-client
# The VM bootstrap points apt at Nexus. Wait for it before the install.
cloud-init status --wait >/dev/null 2>&1 || true
attempt=0
until command -v mysql >/dev/null; do
  attempt=$((attempt + 1))
  [ "$attempt" -le 3 ] || fail
  export DEBIAN_FRONTEND=noninteractive
  if ! { apt-get -o DPkg::Lock::Timeout=300 update -qq && apt-get -o DPkg::Lock::Timeout=300 install -y -qq --no-install-recommends mysql-client-core-8.0; } >/dev/null 2>&1; then
    sleep 30
  fi
done

stage=secret-access
deadline=$(($(date +%s) + 300))
password=""
until [ -n "$password" ]; do
  token=$(curl -sf --max-time 15 -H Metadata:true "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net" |
    python3 -c 'import json, sys; print(json.load(sys.stdin)["access_token"])' 2>/dev/null) || token=""
  if [ -n "$token" ]; then
    password=$(curl -sf --max-time 15 -H "Authorization: Bearer $token" "https://$VAULT_NAME.vault.azure.net/secrets/$SECRET_NAME?api-version=7.4" |
      python3 -c 'import json, sys; print(json.load(sys.stdin)["value"])' 2>/dev/null) || password=""
  fi
  if [ -z "$password" ]; then
    [ "$(date +%s)" -lt "$deadline" ] || fail
    sleep 10
  fi
done
token=""

query() {
  MYSQL_PWD="$password" mysql --host="$SERVER" --user=mysqladmin --database="$DATABASE" \
    --ssl-mode=VERIFY_IDENTITY --ssl-ca=/etc/ssl/certs/ca-certificates.crt \
    --connect-timeout=30 --batch --skip-column-names --execute="$1" 2>/dev/null
}

stage=mysql-connect
query "SELECT 1" >/dev/null || fail

stage=mysql-data
if [ "$PHASE" = write ]; then
  query "CREATE TABLE tre_e2e_probe (probe CHAR(32) NOT NULL PRIMARY KEY); INSERT INTO tre_e2e_probe (probe) VALUES ('$PROBE_ID');" >/dev/null || fail
fi
count=$(query "SELECT COUNT(*) FROM tre_e2e_probe WHERE probe = '$PROBE_ID'") || fail
password=""
[ "$count" = 1 ] || fail
echo "MYSQL_PROBE_RESULT={\"phase\": \"$PHASE\", \"probe\": \"$PROBE_ID\", \"row_count\": $count, \"private_dns\": true}"
