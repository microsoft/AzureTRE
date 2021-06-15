export TF_VAR_docker_registry_server="$ACR_NAME.azurecr.io"
export TF_VAR_docker_registry_username=$ACR_NAME
export TF_VAR_docker_registry_password=$(az acr credential show --name ${ACR_NAME} --query passwords[0].value -o tsv | sed 's/"//g')
export TF_VAR_management_api_image_tag=$IMAGE_TAG

terraform destroy -auto-approve