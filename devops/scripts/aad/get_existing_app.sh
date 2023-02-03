#!/bin/bash

# This script is designed to be `source`d to create reusable helper functions

function show_existing_app_usage()
{
    cat << USAGE

Utility script for retrieve applications in AD; either by name or ID.

Notes: Before Az CLI 2.37 this would return a json document with .objectId; that is now .id

Usage: $0 --name <app-name>
       $0 --id <app-id>
USAGE
    exit 1
}

function get_existing_app() {
    local appName=""
    local appId=""

    while [[ $# -gt 0 ]]; do
      case "$1" in
          --name)
              appName=$2
              shift 2
          ;;
          --id)
              appId=$2
              shift 2
          ;;
          *)
              echo "Invalid option: $1."
              show_existing_app_usage
              exit 2
          ;;
      esac
    done

    existingApiApps="[]"
    if [[ -n "$appName" ]]; then
      existingApiApps=$(az ad app list --display-name "$appName" -o json --only-show-errors)
    else
      if [[ -n "$appId" ]]; then
        existingApiApps=$(az ad app list --app-id "$appId" -o json --only-show-errors)
      fi
    fi

    number_of_apps=$(echo "${existingApiApps}" | jq 'length')

    if [[ "${number_of_apps}" -gt 1 ]]; then
        set -x
        echo "There are more than one applications with the name \"$appName\" already."
        set +x
        return 1
    fi

    if [[ "${number_of_apps}" -eq 1 ]]; then
        echo "${existingApiApps}" | jq -c '.[0]'
        return 0
    fi

    return 0
}
