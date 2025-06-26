#!/bin/bash
set -e

function usage() {
    cat <<USAGE

    Usage: $0 [-d | --directory] [-g | --mgmt-resource-group-name ]  [-s | --mgmt-storage-account-name] [-n | --state-container-name] [-k | --key] [-c | --cmd] [-l | --logfile]

    Options:
        -d, --directory                     Directory to change to before executing commands
        -g, --mgmt-resource-group-name      Management resource group name
        -s, --mgmt-storage-account-name     Management storage account name
        -n, --state-container-name          State container name
        -k, --key                           Key
        -c, --cmd                           Command to execute
        -l, --logfile                       Log file to write output to
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

while [ "$1" != "" ]; do
    case $1 in
    -d | --directory)
        shift
        DIR=$1
        ;;
    -g | --mgmt-resource-group-name)
        shift
        mgmt_resource_group_name=$1
        ;;
    -s | --mgmt-storage-account-name)
        shift
        mgmt_storage_account_name=$1
        ;;
    -n | --state-container-name)
        shift
        container_name=$1
        ;;
    -k | --key)
        shift
        key=$1
        ;;
    -c | --cmd)
        shift
        tf_command=$1
        ;;
    -l | --logfile)
        shift
        tf_logfile=$1
        ;;
    *)
        usage
        ;;
    esac
    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi
    shift # remove the current value for `$1` and use the next
done

if [[ -z ${DIR+x} ]]; then
    echo -e "No directory provided\n"
    usage
fi

if [[ -z ${mgmt_resource_group_name+x} ]]; then
    echo -e "No terraform state resource group name provided\n"
    usage
fi

if [[ -z ${mgmt_storage_account_name+x} ]]; then
    echo -e "No terraform state storage account name provided\n"
    usage
fi

if [[ -z ${container_name+x} ]]; then
    echo -e "No terraform state container name provided\n"
    usage
fi

if [[ -z ${key+x} ]]; then
    echo -e "No key provided\n"
    usage
fi

if [[ -z ${tf_command+x} ]]; then
    echo -e "No command provided\n"
    usage
fi

if [[ -z ${tf_logfile+x} ]]; then
    tf_logfile="tmp$$.log"
    echo -e "No logfile provided, using ${tf_logfile}\n"
fi


# shellcheck disable=SC1091
source "$(dirname "$0")/storage_enable_public_access.sh" \
  --storage-account-name "${mgmt_storage_account_name}" \
  --resource-group-name "${mgmt_resource_group_name}"

# Change directory to $DIR
pushd "$DIR" > /dev/null

terraform init -input=false -backend=true -reconfigure \
    -backend-config="resource_group_name=${mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${mgmt_storage_account_name}" \
    -backend-config="container_name=${container_name}" \
    -backend-config="key=${key}"

RUN_COMMAND=1
while [ $RUN_COMMAND = 1 ]
do
    RUN_COMMAND=0
    TF_CMD="$tf_command"

    script -c "$TF_CMD" "$tf_logfile"

    # upload the log file?
    if [[ $TF_LOG == "DEBUG" ]] ; then
      az storage blob upload --file "$tf_logfile" \
        --container-name "tflogs" \
        --account-name "$mgmt_storage_account_name" \
        --auth-mode key
    fi

    LOCKED_STATE=$(cat < "$tf_logfile" |  grep -c 'Error acquiring the state lock') || true;
    TF_ERROR=$(cat < "$tf_logfile" |  grep -c 'COMMAND_EXIT_CODE="1"') || true;
    if [[ $LOCKED_STATE -gt 0  ]];
    then
        RUN_COMMAND=1
        echo "Error acquiring the state lock"
        sleep 10
    elif [[ $TF_ERROR -gt 0  ]];
    then
        echo "Terraform Error"
        exit 1
    fi
done

# Return to the original directory
popd > /dev/null
