  
#!/bin/bash
# This provisions AML PL and relevant resources and a single no-public-ip compute instance 

terraform init
terraform apply -auto-approve
tfoutput=$(terraform output -json)

resourcegroup=$(echo $tfoutput | jq -r '.resourcegroup.value')
location=$(echo $tfoutput | jq -r '.location.value')
workspace_name=$(echo $tfoutput | jq -r '.workspace_name.value')
computeinstance_name=$(echo $tfoutput | jq -r '.computeinstance_name.value')
computecluster_name=$(echo $tfoutput | jq -r '.computecluster_name.value')
vnet_name=$(echo $tfoutput | jq -r '.vnet_name.value')
subnet_name=$(echo $tfoutput | jq -r '.subnet_name.value')
admin_username=$(echo $tfoutput | jq -r '.admin_username.value')
admin_user_password=$(echo $tfoutput | jq -r '.admin_user_password.value')
jumpbox_ip=$(echo $tfoutput | jq -r '.jumpbox_ip.value')
acr_name=$(echo $tfoutput | jq -r '.acr_name.value')
spn_secret=$(echo $tfoutput | jq -r '.inference_password.value')
app_id=$(echo $tfoutput | jq -r '.inference_app_id.value')
subscription_id=$(echo $tfoutput | jq -r '.subscription_id.value')
tenant_id=$(echo $tfoutput | jq -r '.tenant_id.value')
inference_app=$(echo $tfoutput | jq -r '.inference_app_service.value')

# Deploy one compute insance
az deployment group create -g $resourcegroup \
        --template-file ./nopipcompute/deployplcompute_instance.json \
        --parameters ./nopipcompute/deployplcompute.parameters.json \
        --name amplcomputenpipinst \
        --parameters location=$location \
                     workspace_name=$workspace_name \
                     cluster_name=$computeinstance_name \
                     vnet_name=$vnet_name \
                     subnet_name=$subnet_name \
                     admin_username=$admin_username \
                     admin_user_password=$admin_user_password

# Deploy one compute cluster
az deployment group create -g $resourcegroup \
        --template-file ./nopipcompute/deployplcompute.json \
        --parameters ./nopipcompute/deployplcompute.parameters.json \
        --name amplcomputenpipinst \
        --parameters location=$location \
                     workspace_name=$workspace_name \
                     cluster_name=$computecluster_name \
                     vnet_name=$vnet_name \
                     subnet_name=$subnet_name \
                     admin_username=$admin_username \
                     admin_user_password=$admin_user_password

az extension add -n azure-cli-ml

az ml computetarget amlcompute identity assign --identities '[system]' --name $computecluster_name --workspace-name $workspace_name --resource-group $resourcegroup

sleep 60

computeMSI=$(az ml computetarget amlcompute identity show --name $computecluster_name -w $workspace_name -g $resourcegroup | jq -r '.principalId')

acrScope=$(az resource show -g $resourcegroup -n $acr_name --resource-type 'Microsoft.ContainerRegistry/registries' | jq -r '.id')

az role assignment create --assignee $computeMSI --role acrpull --scope $acrScope

#Clone Inference repo, set config and push to newly created service
git clone https://github.com/microsoft/InnerEye-Inference
cd InnerEye-Inference

inferenceAuthKey=$(uuidgen)

####################
# BUILD INFERENCE CONFIG FILE FROM CONFIG INFORMATION

env_file="set_environment.sh"
cat <<EOF > $env_file 
export CUSTOMCONNSTR_AZUREML_SERVICE_PRINCIPAL_SECRET=$spn_secret
export CUSTOMCONNSTR_API_AUTH_SECRET=$inferenceAuthKey
export CLUSTER=$computecluster_name
export WORKSPACE_NAME=$workspace_name
export EXPERIMENT_NAME=main
export RESOURCE_GROUP=$resourcegroup
export SUBSCRIPTION_ID=$subscription_id
export APPLICATION_ID=$app_id
export TENANT_ID=$tenant_id
export DATASTORE_NAME=inferencetestimagestore
export IMAGE_DATA_FOLDER=temp-image-store 
EOF

az webapp up --name $inference_app -g $resourcegroup

echo "AML and the related resources have been deployed to $resourcegroup.
You can use Firewall IP $jumpbox_ip and port 3389 to connect to the jumpbox 
and access the private AML workspace $workspace_name. 
To authenticate to the jumpbox use:
Username: $admin_username 
Password: $admin_user_password

Your infernce service authentication key is: $inferenceAuthKey and URL is: $inference_app.azurewebsites.net
"
