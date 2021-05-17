# AzureTRE Deployment QuickStart

## Deployment

The AzureTRE uses Terraform infrastructure as code templates that pull down Docker container images to run the web applications.

The most straightforward way to get up and running is to deploy direct from the `microsoft/AzureTRE` repository. Production deployments should take advantage of your chosen DevOps CD tooling.

### Clone the repository

Clone the repository to your local machine ( `git clone https://github.com/microsoft/AzureTRE.git` ) or you may choose to use our preconfigured dev container via GitHub Codespaces.

![Clone Options](../docs/assets/clone_options.png)

### Pre-requisites

You will require the following pre requisites installed. They will already be present if using GitHub CodeSpaces, or use our Dev Container in VSCode.

- Terraform >= v0.15.3.
- Azure CLI >= 2.21.0

You will also need:

- An Azure Subscription
- GitHub user id and [personal access token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) with scope `packages:read`. This token is used to pull the web app Docker images. This can be any GitHub account, and does not need to be part of the Microsoft GitHub organisation. Notice that you might need to enable SSO authorization on the token, depending on the requirements set by your ogranization.

### Configuring variables

In order to run this Terraform configuration you need to set the environment variables in [/templates/core/terraform/terraform.tfvars.tmpl](../templates/core/terraform/terraform.tfvars.tmpl).

Make a copy of the `.terraform.tfvars.tmpl` file, rename it using the format `<environment>.tfvars`. We will use `dev.tfvars`.

Edit the terraform.tfvars as required. As `resource_name_prefix` and `environment` are used in Azure resource names they must be alpha numberic `(a-z,0-9)`. The defaults are as follows:

```hcl
resource_name_prefix     = "tre"
environment              = "dev"
location                 = "westeurope"
address_space            = "10.1.0.0/16"
management_api_image_tag = "develop-latest"
docker_registry_username="YourGitHubUserName"
docker_registry_password="YourGitHubPAT"
```

### Log into your chosen Azure subscription

Login and select the azure subscription you wish to deploy to:

```cmd
az login
az account list
az account set -s <subscription_name_or_id>
```

See [https://docs.microsoft.com/en-us/azure/developer/terraform/get-started-cloud-shell#set-the-current-azure-subscription] for further support.

### Create a Terraform remote state storage

With Terraform remote state, Terraform [stores the state remotely in Azure Storage Container](https://docs.microsoft.com/en-us/azure/developer/terraform/store-state-in-azure-storage). This state file can then be shared between all members of a team when modifying resources using Terraform.

If you do not have an existing Terraform remote state store in Azure, you can run the [create-tf-state.sh](./scripts/create-tf-state.sh) to create the required resources and generate the backend.tfvars file into the /templates folder.

If you have an existing Terraform remote state store in Azure, populate the values in the backend.tfvars file with your Terraform state storage details.

```hcl
resource_group_name  = "rg-terraform-state"
storage_account_name = "tfstate2cb706eb"
container_name = "tfstate"
```

### Initialise Terraform and deploy

To initalise terraform, from the root of the repository run:

```cmd
cd templates/core/terraform
terraform init --backend-config ../../backend.tfvars
```

Create execution plan using your variables file created earlier. Specify a plan file name, we will use `azuretre-dev.tfplan`:

```cmd
terraform plan -var-file dev.tfvars -out azuretre-dev.tfplan
```

Apply the plan:

```cmd
terraform apply azuretre-dev.tfplan
```

### Access the AzureTRE deployment

To get the AzureTRE URL run the following command:

```cmd
terraform output azure_tre_fqdn
```

## Deleting the AzureTRE deployment

To remove the AzureTRE and its resources from your Azure subscription run:

```cmd
terraform destroy -var-file dev.tfvars
```
