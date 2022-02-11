#!/bin/bash
set -e

function usage() {
    cat <<USAGE

    Usage: $0 [-l --lab-name]  [-t --tre_id] [-w --workspace_id] [-n --vm-name] [-i --image-name]

    Options:
        -l, --lab-name:            Name of the DevTest Lab
        -t, --tre_id               ID of the TRE
        -w, --workspace_id         ID of the workspace
        -n, --vm-name              Name of the VM
        -i, --image-name:          Name of the VM Image
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

while [ "$1" != "" ]; do
    case $1 in
    -l | --lab-name)
        shift
        lab_name=$1
        ;;
    -t | --tre-id)
        shift
        tre_id=$1
        ;;
    -w | --workspace-id)
        shift
        workspace_id=$1
        ;;
    -n | --vm-name)
        shift
        vm_name=$1
        ;;
    -i| --image-name)
        shift
        image_name=$1
        ;;
    *)
        echo "Unexpected argument: '$1'"
        usage
        ;;
    esac
    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi
    shift # remove the current value for `$1` and use the next
done

if [[ -z ${lab_name+x} ]]; then
    echo "Lab name is required"
    usage
fi

if [[ -z ${tre_id+x} ]]; then
    echo "TRE ID is required"
    usage
fi

if [[ -z ${workspace_id+x} ]]; then
    echo "Workspace ID is required"
    usage
fi

if [[ -z ${vm_name+x} ]]; then
    echo "VM name is required"
    usage
fi

if [[ -z ${image_name+x} ]]; then
    echo "Image name is required"
    usage
fi

tre_firewall_name="fw-${tre_id}"
tre_firewall_public_ipname="pip-fw-${tre_id}"
core_vnet_name="vnet-${tre_id}"
vm_vnet_name="vnet-${tre_id}-ws-${workspace_id}"
tre_resource_group_name="rg-${tre_id}"
vm_resource_group_name="rg-${tre_id}-ws-${workspace_id}"

az lab vm create --lab-name $lab_name -g $vm_resource_group_name --name $vm_name --image "$image_name" --image-type gallery --size Standard_DS3_v2 --admin-username researcher

VM_ID=$(az lab vm show --lab-name $lab_name -g $vm_resource_group_name --name $vm_name -o json --query computeId  | tr -d '"')
PRIVATE_IP=$(az vm show --ids $VM_ID -d -o json --query privateIps  | tr -d '"')
RANDOM_PORT=$(shuf -i 2000-65000 -n 1)
FIREWALL_PUBLIC_IP=$(az network public-ip show -n $tre_firewall_public_ipname -g $tre_resource_group_name -o json --query ipAddress  | tr -d '"')
FIREWALL_SUBNET_ADDRESS_PREFIX=$(az network vnet subnet show --vnet-name $core_vnet_name -n AzureFirewallSubnet -g $tre_resource_group_name -o json --query addressPrefix  | tr -d '"')
VM_SUBNET_ADDRESS_PREFIX=$(az network vnet subnet show --vnet-name $vm_vnet_name -n ServicesSubnet -g $vm_resource_group_name -o json --query addressPrefix  | tr -d '"')
SOURCE_IP=$(curl ifconfig.co)

# check if NAT rule already exists
if NAT_RULE=$(az network firewall nat-rule show --resource-group $tre_resource_group_name --firewall-name $tre_firewall_name --collection-name "nrc-$lab_name" --name $vm_name -o json); then
    echo "NAT rule already exists for this VM please delete"
else
    # change command if rule collection already exists
    if RULE_COLLECTION=$(az network firewall nat-rule list --resource-group $tre_resource_group_name --firewall-name $tre_firewall_name --collection-name "nrc-$lab_name" -o json); then
        echo "adding rule to existing collection"
        az network firewall nat-rule create --collection-name "nrc-$lab_name" --name $vm_name --destination-ports $RANDOM_PORT --translated-address $PRIVATE_IP --translated-port 3389 --source-addresses $SOURCE_IP --destination-addresses $FIREWALL_PUBLIC_IP --resource-group $tre_resource_group_name --firewall-name $tre_firewall_name --protocols Any
    else
        NAT_RULE_MAX_PRIORITY=$(az network firewall nat-rule collection list --resource-group $tre_resource_group_name --firewall-name $tre_firewall_name  -o json --query 'not_null(max_by([],&priority).priority) || `100`')
        NAT_RULE_PRIORITY=$(($NAT_RULE_MAX_PRIORITY+1))
        echo "creating new rule collection and rule"
        az network firewall nat-rule create --collection-name "nrc-$lab_name" --priority $NAT_RULE_PRIORITY --action Dnat --name $vm_name --destination-ports $RANDOM_PORT --translated-address $PRIVATE_IP --translated-port 3389 --source-addresses $SOURCE_IP --destination-addresses $FIREWALL_PUBLIC_IP --resource-group $tre_resource_group_name --firewall-name $tre_firewall_name --protocols Any
    fi
fi

# check if NSG rule already exists
if NSG_RULE=$(az network nsg rule show -g $vm_resource_group_name --nsg-name nsg-ws --name $lab_name -o json); then
    echo "NSG rule from firewall already exists for VMs in this worksapce"
else
    az network nsg rule create -g $vm_resource_group_name --nsg-name nsg-ws --name $lab_name --priority 800 --destination-port-range 3389 --source-address-prefixes $FIREWALL_SUBNET_ADDRESS_PREFIX --destination-address-prefixes $VM_SUBNET_ADDRESS_PREFIX --protocol Tcp --access Allow
fi


echo "VM has been been deployed. You can use IP $FIREWALL_PUBLIC_IP and port $RANDOM_PORT to connect to the VM with username "researcher", and password supplied."

