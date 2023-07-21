#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

if [[ -z ${DATA_SOURCE_CONFIG:-} ]] || [[ -z ${DATA_SOURCE_DIAMONS:-} ]]; then
  printf 'No data source or daimons configured.'
  exit 0
else
  # Parse Data source
  ds_config="$(echo "$DATA_SOURCE_CONFIG" | base64 --decode)"
  ds_daimons="$(echo "$DATA_SOURCE_DIAMONS" | base64 --decode)"
  dialect="$(jq -r '.dialect' <<< "$ds_config")"

  if [[ $dialect != "Azure Synapse" ]]; then
    printf 'Not a Synapse data source, no action required.'
    exit 0
  fi

  origin_results_schema_name="$(jq -r '.daimon_results' <<< "$ds_daimons")"
  origin_temp_schema_name="$(jq -r '.daimon_temp' <<< "$ds_daimons")"
  if [[ -z $origin_results_schema_name ]] || [[ -z $origin_temp_schema_name ]]; then
    printf 'Results and temp schemas are not configured.'
    exit 0
  fi

  # Parse required info
  admin_user="$(jq -r '.username' <<< "$ds_config")"
  jdbc_connection_string="$(jq -r '.connection_string' <<< "$ds_config")"
  synapse_server="$([[ $jdbc_connection_string =~ jdbc:sqlserver://(.*):1433 ]] &&  echo "${BASH_REMATCH[1]}")"
  synapse_db="$([[ $jdbc_connection_string =~ database=(.*)(;user) ]] &&  echo "${BASH_REMATCH[1]}")"
  origin_results_schema_name="$(jq -r '.daimon_results' <<< "$ds_daimons")"
  origin_temp_schema_name="$(jq -r '.daimon_temp' <<< "$ds_daimons")"
  parsed_resource_id="$(echo "$TRE_RESOURCE_ID" | tr - _ )"
  results_schema_name="${origin_results_schema_name}_${parsed_resource_id}"
  temp_schema_name="${origin_temp_schema_name}_${parsed_resource_id}"

  # Export password as required by sqlcmd tool
  # shellcheck disable=SC2155
  export SQLCMDPASSWORD="$(jq -r '.password' <<< "$ds_config")"

  printf 'Execute Synapse SQL script'
  sqlcmd -U "${admin_user}" -S "${synapse_server}" -d "${synapse_db}" -W -v RESULTS_SCHEMA_NAME="${results_schema_name}" -v TEMP_SCHEMA_NAME="${temp_schema_name}" -v ORIGIN_RESULTS_SCHEMA_NAME="${origin_results_schema_name}" -i "${SCRIPT_PATH}"
  printf 'Execute Synapse SQL script: done.'
  exit 0
fi
