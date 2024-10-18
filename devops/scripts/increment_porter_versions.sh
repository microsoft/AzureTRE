#!/bin/bash

# Directory containing the porter.yaml files
TEMPLATES_DIR="./templates"

# Function to increment the version number
increment_version() {
  local version=$1
  local major minor patch
  IFS='.' read -r major minor patch <<< "$version"
  patch=$((patch + 1))
  echo "$major.$minor.$patch"
}

# Find all porter.yaml files in the templates directory
find "$TEMPLATES_DIR" -name "porter.yaml" | while read -r file; do
  # Read the current version from the file
  current_version=$(grep -E '^version: ' "$file" | awk '{print $2}')

  # Increment the version number
  new_version=$(increment_version "$current_version")

  # Update the version number in the file
  sed -i "s/version: $current_version/version: $new_version/" "$file"

  echo "Updated $file from version $current_version to $new_version"
done
