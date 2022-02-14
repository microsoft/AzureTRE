# Azure DevTest Labs Service bundle

See: [https://azure.microsoft.com/services/devtest-lab/](https://azure.microsoft.com/services/devtest-lab/)

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)

## Manual Deployment

!!! caution
    Resources should be deployed using the API (i.e. through the Swagger UI as described in the [setup instructions](../../tre-admins/setup-instructions/installing-workspace-service-and-user-resource.md)). Only deploy manually for development/testing purposes.

1. Create a copy of `templates/workspace_services/devtestlabs/.env.sample` with the name `.env` and update with the Workspace ID used when deploying the base workspace.

  | Environment variable name | Description |
  | ------------------------- | ----------- |
  | `ID` | A GUID to identify the workspace service. The last 4 characters of this `ID` can be found in the resource names of the workspace service resources. |
  | `WORKSPACE_ID` | The GUID identifier used when deploying the base workspace bundle. |

1. Build and install the Azure DevTest Labs Service bundle

  ```cmd
  make porter-build DIR=./templates/workspace_services/devtestlabs
  make porter-install DIR=./templates/workspace_services/devtestlabs
  ```

## Create and expose a VM via the Firewall

When this service used without a virtual desktop gateway it might be necessary to manually create and expose a VM via the TRE firewall. This method of exposing VMs is not recommended for large scale deployments given there will be multiple resources and rules to manually manage.

1. Create a DevTest Labs VM and open a port in the TRE firewall using the script provided.

    ```cmd
    Usage:
        ./create_and_expose_vm.sh [-l --lab-name]  [-t --tre_id] [-w --workspace_id] [-n --vm-name] [-i --image-name]

    Options:
        -l, --lab-name:            Name of the DevTest Lab
        -t, --tre_id               ID of the TRE
        -w, --workspace_id         ID of the workspace
        -n, --vm-name              Name of the VM
        -i, --image-name:          Name of the VM Image

    Example:

    ./templates/workspace_services/devtestlabs/create_and_expose_vm.sh --lab-name <lab_name> --tre-id <tre-id> --workspace-id <workspace-id> --vm-name <vmn-name> --image-name "Data Science Virtual Machine - Windows Server 2019"

    ```

2. Using the details provided by the script, and a remote desktop connection client connect to the VM.
