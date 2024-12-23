#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

VALIDITY_DAYS=1095

#
# generate CA key, csr and cert & convert to pfx
#
function generate_ca() {
 local CA_COMMON_NAME=$1
 local CA_VALIDITY_DAYS=$2

 local CA_FILENAME_PREFIX=$CA_COMMON_NAME
 local CA_SUBJECT="/C=/ST=/L=/O=Microsoft/OU=AzureTRE/CN=$CA_COMMON_NAME"
 local OPENSSL_CONF
 OPENSSL_CONF="$(get_ca_openssl_conf)"

 echo -e "Generating CA private key..."
 openssl ecparam -out $CA_FILENAME_PREFIX.key -name prime256v1 -genkey

 echo -e "\nGenerating signing request..."
 openssl req -new -nodes -sha256 -key $CA_FILENAME_PREFIX.key -out $CA_FILENAME_PREFIX.csr -subj $CA_SUBJECT

 echo -e "\nGenerating CA certificate..."
 openssl x509 -req -sha256 -days $CA_VALIDITY_DAYS -in $CA_FILENAME_PREFIX.csr -signkey $CA_FILENAME_PREFIX.key -out $CA_FILENAME_PREFIX.crt -extfile <(echo "$OPENSSL_CONF") -extensions ca

 echo -e "\nConverting CA key and certificate to pfx..."
 openssl pkcs12 -export -password pass: -out $CA_FILENAME_PREFIX.pfx -inkey $CA_FILENAME_PREFIX.key -in $CA_FILENAME_PREFIX.crt
}


#
# generate leaf key, csr and CA signed certificate & convert to pfx
#
function generate_leaf() {

 local LEAF_COMMON_NAME=$1
 local LEAF_VALIDITY_DAYS=$2
 local LEAF_SUBJECT_ALT=$3
 local CA_COMMON_NAME=$4

 local LEAF_FILENAME_PREFIX=$LEAF_COMMON_NAME
 local LEAF_SUBJECT="/C=/ST=/L=/O=Microsoft/OU=AzureTRE/CN=$LEAF_COMMON_NAME"
 local CA_FILENAME_PREFIX=$CA_COMMON_NAME
 local OPENSSL_CONF
 OPENSSL_CONF="$(get_leaf_openssl_conf $LEAF_SUBJECT_ALT)"

 echo -e "\nGenerating leaf private key..."
 openssl ecparam -out $LEAF_FILENAME_PREFIX.key -name prime256v1 -genkey

 echo -e "\nGenerating leaf signing request..."
 openssl req -new -sha256 -nodes -key $LEAF_FILENAME_PREFIX.key -out $LEAF_FILENAME_PREFIX.csr -subj $LEAF_SUBJECT

 echo -e "\nGenerating leaf certificate and signing with CA..."
 openssl x509 -req -sha256 -days $LEAF_VALIDITY_DAYS -in $LEAF_FILENAME_PREFIX.csr -CA $CA_FILENAME_PREFIX.crt \
     -CAkey $CA_FILENAME_PREFIX.key -CAcreateserial -out $LEAF_FILENAME_PREFIX.crt -extfile <(echo "$OPENSSL_CONF") -extensions server

 echo -e "\nConverting leaf key, leaf certificate, and CA certificate to pfx..."
 openssl pkcs12 -export -password pass: -out $LEAF_FILENAME_PREFIX.pfx -inkey $LEAF_FILENAME_PREFIX.key -in $LEAF_FILENAME_PREFIX.crt -certfile $CA_FILENAME_PREFIX.crt

}

function get_ca_openssl_conf() {

 local OPENSSL_CONF
 OPENSSL_CONF="$(cat <<EOF
[ ca ]
# X509 extensions for a ca
keyUsage                = critical, cRLSign, keyCertSign
basicConstraints        = CA:TRUE, pathlen:0
subjectKeyIdentifier    = hash
authorityKeyIdentifier  = keyid:always,issuer:always
EOF
)"

 echo "$OPENSSL_CONF"

}

function get_leaf_openssl_conf() {

 local LEAF_SUBJECT_ALT=$1
 local OPENSSL_CONF
 OPENSSL_CONF="$(cat <<EOF
[ server ]
# X509 extensions for a server
keyUsage                = critical,digitalSignature
extendedKeyUsage        = serverAuth,clientAuth
basicConstraints        = critical,CA:FALSE
subjectKeyIdentifier    = hash
authorityKeyIdentifier  = keyid,issuer:always
subjectAltName          = $LEAF_SUBJECT_ALT
EOF
)"

# nb removed 'keyUsage = keyEncipherment' as key vault does not accept

 echo "$OPENSSL_CONF"
}

function upload_cert_to_kv() {

  local KV_NAME=$1
  local CERT_COMMON_NAME=$2
  local PFX_FILENAME=$3

  echo -e "\nUploading $PFX_FILENAME to keyvayult $KV_NAME..."

  (az keyvault certificate recover --vault-name "$KV_NAME" --name "$CERT_COMMON_NAME" && sleep 15) || true

  az keyvault certificate import \
    --vault-name "$KV_NAME" \
    --name "$CERT_COMMON_NAME" \
    --file "$PFX_FILENAME"
}

echo "Exists is: ${CA_CERT_EXISTS}"

if [ "${CA_CERT_EXISTS}" == "1" ]; then
  echo "CA Certificate exists, skipping creation"
  exit 0
fi

generate_ca "$CA_COMMON_NAME" "$VALIDITY_DAYS"
upload_cert_to_kv "$KV_NAME" "$KV_CERT_PREFIX-$CA_COMMON_NAME" "$CA_COMMON_NAME.pfx"

for item in ${LEAF_IPS}; do
  echo "$item"
  generate_leaf "$item" "$VALIDITY_DAYS" "IP:$item" "$CA_COMMON_NAME"
  upload_cert_to_kv "$KV_NAME" "$KV_CERT_PREFIX-${item//./-}" "$item.pfx"
done

rm -f ./*.key ./*.csr ./*.crt ./*.pfx ./*.srl
