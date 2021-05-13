# AzureTRE Deployment QuickStart

## Deployment
The AzureTRE uses Terraform infrastructure as code templates that pull down Docker container images to run the web applications.

The most straightforward way to get up and running is to deploy direct from the `microsoft/AzureTRE` repository. Production deployments should take advantage of your chosen DevOps CD tooling.

### Clone the repository
Clone the repository to to your local machine ( `git clone https://github.com/microsoft/AzureTRE.git` ) or you may choose to use our preconfigured dev container via GitHub Codespaces.

![Clone Options](../docs/assets/clone_options.png)

### Pre-requisites:

You will require the following pre requisites installed. They will already be present if using GitHub CodeSpaces, or use our Dev Container in VSCode.
- Terraform >= v0.15.3. The following instructions use local terraform state, you may want to consider [storing you state remotely in Azure](https://docs.microsoft.com/en-us/azure/developer/terraform/store-state-in-azure-storage)
- Azure CLI >= 2.21.0

You will also need:
- An Azure Subscription
- GitHub user id and [personal access token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) with scope `packages:read`. This token is used to by the web apps pull the Docker images. This can be any GitHub account, and does not need to be part of the Microsoft GitHub organisation.


### Configuring variables
In order to run this Terraform configuration you need to set the environment variables in [/templates/core/terraform/terraform.tfvars.tmpl](../templates/core/terraform/terraform.tfvars.tmpl).

Make a copy of the `.terraform.tfvars.tmpl` file, rename it using the format `<environment>.tfvars`. We will use `dev.tfvars`.

Edit the terraform.tfvars as required, the defaults are as follows:

```hcl
resource_name_prefix     = "tre"
environment              = "dev"
location                 = "westeurope"
address_space            = "10.1.0.0/16"
management_api_image_tag = "develop-latest"
```

### Log into your chosen Azure subscription
Login and selct the azure subscription you wish to deploy to:

```
az login
az account list
az account set -s <subscription_name_or_id>
```

See [https://docs.microsoft.com/en-us/azure/developer/terraform/get-started-cloud-shell#set-the-current-azure-subscription] for further support.

### Initialise Terraform and deploy

To initalise terraform, from the root of the repository run:

```cmd
cd templates/core/terraform
terraform init
```

Create execution plan using your variables file created earlier. Specify a plan file name, we will use `azuretre-dev.tfplan`:

```cmd
terraform plan -var-file dev.tfvars -out azuretre-dev.tfplan
```

You will be prompted for your GitHub username and PAT token.

Apply the plan:
```cmd
terraform apply azuretre-dev.tfplan
```

### Access the AzureTRE deployment

Do get the AzureTRE URL run the following command:

```cmd
terraform output azure_tre_fqdn
```

## Deleting the AzureTRE deployment

To remove the AzureTRE and it's resources from your Azure subscription run:

```cmd
terraform destroy -var-file dev.tfvars
```