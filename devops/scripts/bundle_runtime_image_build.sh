#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

# Check for import section (import image from external registry to ACR)
if [ "$(yq eval ".custom.runtime_image.import" porter.yaml)" != "null" ]; then
  image_name=$(yq eval ".custom.runtime_image.name" porter.yaml)
  source_image=$(yq eval ".custom.runtime_image.import.source" porter.yaml)
  version=$(yq eval ".custom.runtime_image.import.tag" porter.yaml)

  # Skip import if the image already exists in ACR (avoids Docker Hub rate limits).
  # Errors from show-tags (e.g. repository not yet created) are suppressed intentionally:
  # any failure means we cannot confirm the image is cached and we fall through to the
  # import step, which will surface real auth or network problems with a clear error.
  if az acr repository show-tags \
    --name "${ACR_NAME}" \
    --repository "${image_name}" \
    --query "[?@=='${version}'] | [0]" \
    --output tsv 2>/dev/null | grep -qx "${version}"; then
    echo "Image ${image_name}:${version} already exists in ACR ${ACR_NAME}; skipping import"
    exit 0
  fi

  echo "Importing ${source_image}:${version} to ACR as ${image_name}:${version}..."
  az acr import --name "${ACR_NAME}" \
    --source "${source_image}:${version}" \
    --image "${image_name}:${version}" \
    --force
  echo "Image imported successfully"
  exit 0
fi

if [ "$(yq eval ".custom.runtime_image.build" porter.yaml)" == "null" ]; then
  echo "Runtime image build section isn't specified. Exiting..."
  exit 0
fi

image_name=$(yq eval ".custom.runtime_image.name" porter.yaml)
version_file=$(yq eval ".custom.runtime_image.build.version_file" porter.yaml)
docker_file=$(yq eval ".custom.runtime_image.build.docker_file" porter.yaml)
docker_context=$(yq eval ".custom.runtime_image.build.docker_context" porter.yaml)
acr_domain_suffix=$(az cloud show --query suffixes.acrLoginServerEndpoint --output tsv)

version_line=$(cat "${version_file}")

# doesn't work with quotes
# shellcheck disable=SC2206
version_array=( ${version_line//=/ } ) # split by =
version="${version_array[1]//\"}" # second element is what we want, remove " chars

az acr login -n "${ACR_NAME}"

docker_cache=("--cache-from" "${FULL_IMAGE_NAME_PREFIX}/${image_name}:${version}")

if [ -n "${CI_CACHE_ACR_NAME:-}" ]; then
	az acr login -n "${CI_CACHE_ACR_NAME}"
	docker_cache+=("--cache-from" "${CI_CACHE_ACR_NAME}${acr_domain_suffix}/${IMAGE_NAME_PREFIX}/${image_name}:${version}")
fi

ARCHITECTURE=$(docker info --format "{{ .Architecture }}" )

if [ "${ARCHITECTURE}" == "aarch64" ]; then
    DOCKER_BUILD_COMMAND="docker buildx build --platform linux/amd64"
else
    DOCKER_BUILD_COMMAND="docker build"
fi

${DOCKER_BUILD_COMMAND} --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t "${FULL_IMAGE_NAME_PREFIX}/${image_name}:${version}" \
  "${docker_cache[@]}" -f "${docker_file}" "${docker_context}"

