#!/bin/bash

# Configure Nexus to use certificate to serve proxies over https

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

echo "Setting up Nexus SSL..."

# Import ssl cert to keystore within Nexus volume
keystore_timeout=60
echo 'Checking for nexus-data/keystores directory...'
while [ ! -d /etc/nexus-data/keystores ]; do
  # Wait for /keystore dir to be created by container first
  if [ $keystore_timeout == 0 ]; then
    echo 'ERROR - Timeout while waiting for Nexus to create nexus-data/keystores'
    exit 1
  fi
  sleep 5
  ((keystore_timeout--))
done

downloaded_cert_path="/var/lib/waagent/Microsoft.Azure.KeyVault.Store/${VAULT_NAME}.${SSL_CERT_NAME}"
cert_timeout=60
echo 'Waiting for cert to be downloaded from KV...'
while [ ! -f "$downloaded_cert_path" ]; do
  if [ $cert_timeout == 0 ]; then
    echo 'ERROR - Timeout while waiting!'
    exit 1
  fi
  sleep 5
  ((cert_timeout--))
done

keystore_file_name=ssl.keystore
cert_password=$(openssl rand -base64 32)
rm -f temp.p12
openssl pkcs12 -export -inkey "$downloaded_cert_path" -in "$downloaded_cert_path" -out temp.p12 -password "pass:$cert_password"
rm -f /etc/nexus-data/keystores/"$keystore_file_name"
keytool -v -importkeystore -noprompt -srckeystore temp.p12 -srcstoretype PKCS12 -srcstorepass "$cert_password" \
  -destkeystore /etc/nexus-data/keystores/"$keystore_file_name" -deststoretype PKCS12 -deststorepass "$cert_password"
rm -f temp.p12

# Configure Jetty instance within Nexus to consume ssl cert
echo 'Modifying Nexus Jetty configuration to enable ssl...'
mkdir -p /etc/nexus-data/etc/jetty
# -- first need to copy default Jetty config to persistent volume so isn't overwritten on restart
docker exec -u root nexus cp /opt/sonatype/nexus/etc/jetty/jetty-https.xml /nexus-data/etc/jetty/
# -- then we replace password values with the ssl cert keystore password
xmlstarlet ed -P --inplace \
  -u "/Configure[@id='Server']/New[@id='sslContextFactory']/Set[@name='KeyStorePassword']" \
  -v "$cert_password" /etc/nexus-data/etc/jetty/jetty-https.xml
xmlstarlet ed -P --inplace \
  -u "/Configure[@id='Server']/New[@id='sslContextFactory']/Set[@name='KeyManagerPassword']" \
  -v "$cert_password" /etc/nexus-data/etc/jetty/jetty-https.xml
xmlstarlet ed -P --inplace \
  -u "/Configure[@id='Server']/New[@id='sslContextFactory']/Set[@name='TrustStorePassword']" \
  -v "$cert_password" /etc/nexus-data/etc/jetty/jetty-https.xml
# -- then update the location of our keystore
xmlstarlet ed -P --inplace \
  -u "/Configure[@id='Server']/New[@id='sslContextFactory']/Set[@name='KeyStorePath']" \
  -v /nexus-data/keystores/"$keystore_file_name" /etc/nexus-data/etc/jetty/jetty-https.xml
xmlstarlet ed -P --inplace \
  -u "/Configure[@id='Server']/New[@id='sslContextFactory']/Set[@name='TrustStorePath']" \
  -v /nexus-data/keystores/"$keystore_file_name" /etc/nexus-data/etc/jetty/jetty-https.xml

# Add jetty configuration and ssl port to Nexus properties
cat >> /etc/nexus-data/etc/nexus.properties <<'EOF'
application-port-ssl=8443
nexus-args=$${jetty.etc}/jetty.xml,$${jetty.etc}/jetty-http.xml,$${jetty.etc}/jetty-requestlog.xml,/nexus-data/etc/jetty/jetty-https.xml
EOF

# Restart the container for changes to take effect
docker restart nexus
echo 'Nexus ssl configuration completed.'
