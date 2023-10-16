#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

function template_version () {
  version=$(yq eval ".version" "$1")
  name=$(yq eval ".name" "$1")
  echo -e "| $name | $version |"
}

function component_version () {
  version_line=$(cat "$2")

  # doesn't work with quotes
  # shellcheck disable=SC2206
  version_array=( ${version_line//=/ } ) # split by =
  version="${version_array[1]//\"}" # second element is what we want, remove " chars
  echo -e "| $1 | $version |"
}

function ui_version () {
  # get version from ./ui/app/package.json
  version=$(yq -oy eval ".version" "./ui/app/package.json")
  echo -e "| ui | $version |"
}


echo -e "| name | version |\n| ----- | ----- |"

component_version "devops" "devops/version.txt"
component_version "core" "core/version.txt"
ui_version

find . -type f -name "porter.yaml" -not -path "*/.cnab/*" -print0 | sort | while read -r -d $'\0' file
do
  template_version "$file"
done



