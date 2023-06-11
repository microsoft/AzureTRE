#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

function build_daimon_object() {
  local DAIMON_TYPE=$1
  local VALUE=$2

  echo '{
    "tableQualifier": "'"$VALUE"'",
    "priority": 0,
    "sourceDaimonId": null,
    "daimonType": "'"$DAIMON_TYPE"'"
  }'
}


# Login
login_response=$(curl "https://${OHDSI_WEB_API_URL}/WebAPI/user/login/db" \
  --data-raw "login=$OHDSI_WEB_API_USER&password=$OHDSI_WEB_API_PASSWORD" \
  --compressed -i)

token=$(echo "$login_response" | grep -i bearer: | sed 's/Bearer: //' | tr -d '[:space:]')


# Build the request payload
JSON_PAYLOAD="{}"
JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.dialect = $DIALECT' --arg DIALECT "$DIALECT")
JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.name = $SOURCE_NAME' --arg SOURCE_NAME "$SOURCE_NAME")
JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.key = $SOURCE_KEY' --arg SOURCE_KEY "$SOURCE_KEY")
JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.connectionString = $CONNECTION_STRING' --arg CONNECTION_STRING "$CONNECTION_STRING")
JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.username = $USERNAME' --arg USERNAME "$USERNAME")
JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.password = $PASSWORD' --arg PASSWORD "$PASSWORD")
JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.krbAuthMethod = "password"')
JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.krbAdminServer = null')
JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.daimons = []')

if [[ -v DAIMON_CDM ]]; then
  JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.daimons += [$DAIMON_CDM]' --argjson DAIMON_CDM "$(build_daimon_object "CDM" "${DAIMON_CDM}")")
fi

if [[ -v DAIMON_VOCABULARY ]]; then
  JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.daimons += [$DAIMON_VOCABULARY]' --argjson DAIMON_VOCABULARY "$(build_daimon_object "Vocabulary" "${DAIMON_VOCABULARY}")")
fi

if [[ -v DAIMON_RESULTS ]]; then
  JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.daimons += [$DAIMON_RESULTS]' --argjson DAIMON_RESULTS "$(build_daimon_object "Results" "${DAIMON_RESULTS}")")
fi

if [[ -v DAIMON_CEM ]]; then
  JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.daimons += [$DAIMON_CEM]' --argjson DAIMON_CEM "$(build_daimon_object "CEM" "${DAIMON_CEM}")")
fi

if [[ -v DAIMON_CEM_RESULTS ]]; then
  JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.daimons += [$DAIMON_CEM_RESULTS]' --argjson DAIMON_CEM_RESULTS "$(build_daimon_object "CEMResults" "${DAIMON_CEM_RESULTS}")")
fi

if [[ -v DAIMON_TEMP ]]; then
  JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq '.daimons += [$DAIMON_TEMP]' --argjson DAIMON_TEMP "$(build_daimon_object "Temp" "${DAIMON_TEMP}")")
fi


# Add the data source
curl -v "https://${OHDSI_WEB_API_URL}/WebAPI/source/" \
  -H "Authorization: Bearer ${token}" \
  -H 'Content-Type: multipart/form-data; boundary=----WebKitFormBoundary2C72lleJPQ9UH4DL' \
  --data-raw $'------WebKitFormBoundary2C72lleJPQ9UH4DL\r\nContent-Disposition: form-data; name="keyfile"\r\n\r\nundefined\r\n------WebKitFormBoundary2C72lleJPQ9UH4DL\r\nContent-Disposition: form-data; name="source"; filename="blob"\r\nContent-Type: application/json\r\n\r\n'"${JSON_PAYLOAD}"$'\r\n------WebKitFormBoundary2C72lleJPQ9UH4DL--\r\n' \
  --compressed
