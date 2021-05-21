ACR_NAME="${TF_VAR_resource_name_prefix}acr"
export TF_VAR_docker_registry_server="${TF_VAR_resource_name_prefix}acr.azurecr.io"
export TF_VAR_docker_registry_username="${TF_VAR_resource_name_prefix}acr"
export TF_VAR_docker_registry_password=$(az acr credential show --name ${TF_VAR_resource_name_prefix}acr --query passwords[0].value | sed 's/"//g')
export TF_VAR_management_api_image_tag=$TF_VAR_image_tag

terraform destroy -auto-approve