#!/bin/bash

# Configure Nexus to use certificate to serve proxies over https

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# Prepare ssl certificate
az login --identity -u "${msi_id}" --allow-no-subscriptions
# -- get cert from kv as secret so it contains private key
echo 'Getting cert and cert password from Keyvault...'
az keyvault secret download --vault-name "${vault_name}" --name "${ssl_cert_name}" --file temp.pfx --encoding base64
CERT_PASSWORD=$(az keyvault secret show --vault-name "${vault_name}" \
  --name "${ssl_cert_password_name}" -o tsv --query value)
# -- az cli strips out password from cert so we re-add by converting to PEM then PFX with pwd
openssl pkcs12 -in temp.pfx -out temp.pem -nodes -password pass:
openssl pkcs12 -export -out nexus-ssl.pfx -in temp.pem -password "pass:$CERT_PASSWORD"

# Import ssl cert to keystore within Nexus volume
keystore_timeout=300
echo 'Checking for nexus-data/keystores directory...'
while [ ! -d /etc/nexus-data/keystores ]; do
  # Wait for /keystore dir to be created by container first
  if [ $keystore_timeout == 0 ]; then
    echo 'ERROR - Timeout while waiting for Nexus to create nexus-data/keystores'
    exit 1
  fi
  sleep 1
  ((keystore_timeout--))
done
echo 'Directory found. Importing ssl cert into nexus-data/keystores/keystore.jks...'
keytool -v -importkeystore -noprompt -srckeystore nexus-ssl.pfx -srcstoretype PKCS12 \
  -destkeystore /etc/nexus-data/keystores/keystore.jks \
  -deststoretype JKS -srcstorepass "$CERT_PASSWORD" -deststorepass "$CERT_PASSWORD"

# Configure Jetty instance within Nexus to consume ssl cert
echo 'Modifying Nexus Jetty configuration to enable ssl...'
mkdir -p /etc/nexus-data/etc/jetty
# -- first need to copy default Jetty config to persistent volume so isn't overwritten on restart
docker exec -u root nexus cp /opt/sonatype/nexus/etc/jetty/jetty-https.xml /nexus-data/etc/jetty/
# -- then we replace password values with the ssl cert keystore password
xmlstarlet ed -P --inplace \
  -u "/Configure[@id='Server']/New[@id='sslContextFactory']/Set[@name='KeyStorePassword']" \
  -v "$CERT_PASSWORD" /etc/nexus-data/etc/jetty/jetty-https.xml
xmlstarlet ed -P --inplace \
  -u "/Configure[@id='Server']/New[@id='sslContextFactory']/Set[@name='KeyManagerPassword']" \
  -v "$CERT_PASSWORD" /etc/nexus-data/etc/jetty/jetty-https.xml
xmlstarlet ed -P --inplace \
  -u "/Configure[@id='Server']/New[@id='sslContextFactory']/Set[@name='TrustStorePassword']" \
  -v "$CERT_PASSWORD" /etc/nexus-data/etc/jetty/jetty-https.xml
# -- then update the location of our keystore
xmlstarlet ed -P --inplace \
  -u "/Configure[@id='Server']/New[@id='sslContextFactory']/Set[@name='KeyStorePath']" \
  -v /nexus-data/keystores/keystore.jks /etc/nexus-data/etc/jetty/jetty-https.xml
xmlstarlet ed -P --inplace \
  -u "/Configure[@id='Server']/New[@id='sslContextFactory']/Set[@name='TrustStorePath']" \
  -v /nexus-data/keystores/keystore.jks /etc/nexus-data/etc/jetty/jetty-https.xml

# Add jetty configuration and ssl port to Nexus properties
cat >> /etc/nexus-data/etc/nexus.properties <<'EOF'
application-port-ssl=8443
nexus-args=$${jetty.etc}/jetty.xml,$${jetty.etc}/jetty-http.xml,$${jetty.etc}/jetty-requestlog.xml,/nexus-data/etc/jetty/jetty-https.xml
EOF

# Restart the container for changes to take effect
docker restart nexus
echo 'Nexus ssl configuration completed.'
