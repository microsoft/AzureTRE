#!/bin/bash
set -eu

register_template() {
  local template_dir=$1
  local bundle_name
  bundle_name=$(basename "$template_dir")
  local bundle_type=$2
  local parent_bundle=$3

  if [ -f "$template_dir"/porter.yaml ]; then
    if [ "$bundle_type" == "$parent_bundle" ]; then
      echo "Registering $bundle_type bundle $bundle_name"
      until make "${bundle_type%s}"_bundle BUNDLE="$bundle_name"; do
        [[ $? == 2 ]] || break
      done
    else
      echo "Registering user resource bundle $bundle_name for workspace service $parent_bundle"
      until make user_resource_bundle BUNDLE="$bundle_name" WORKSPACE_SERVICE="$parent_bundle"; do
        [[ $? == 2 ]] || break
      done
    fi
  fi
}

for template_type_dir in $(find ./templates -mindepth 1 -maxdepth 1 -type d); do
  template_type=$(basename "$template_type_dir")
  echo "Registering $template_type"
  for template_dir in $(find ./templates/$template_type -mindepth 1 -maxdepth 1 -type d); do
    template_name=$(basename "$template_dir")
    echo "Registering $template_name $template_type template"
    register_template "$template_dir" "$template_type" "$template_type"

    if [[ "$template_type" == "workspace_services" ]] && [ -d "$template_dir/user_resources" ]; then
      echo "Registering user resources for $template_name"
      for user_resource_template_dir in $(find $template_dir/user_resources -mindepth 1 -maxdepth 1 -type d); do
        register_template "$user_resource_template_dir" "user_resource" "$template_name"
      done
    fi
  done
done
