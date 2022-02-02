export TF_VAR_docker_registry_server="$TF_VAR_acr_name.azurecr.io"
export TF_VAR_docker_registry_username=$TF_VAR_acr_name
export TF_VAR_docker_registry_password=$(az acr credential show --name ${TF_VAR_acr_name} --query passwords[0].value -o tsv | sed 's/"//g')

../../../devops/scripts/terraform_wrapper.sh -g $TF_VAR_mgmt_resource_group_name \
                                             -s $TF_VAR_mgmt_storage_account_name \
                                             -n $TF_VAR_terraform_state_container_name \
                                             -k $TRE_ID -c "terraform destroy -auto-approve"
