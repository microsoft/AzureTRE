# Deploying Azure TRE

You are now ready to deploy the Azure TRE instance. Execute the `all` action of the makefile using `make`:

```bash
make all
```

Deploying a new Azure TRE instance takes approximately 30 minutes.

Once the deployment is completed, you will be presented with a few output variables similar to the ones below:

```plaintext
app_gateway_name = "agw-mytre"
azure_tre_fqdn = "mytre.westeurope.cloudapp.azure.com"
core_resource_group_name = "rg-mytre"
keyvault_name = "kv-mytre"
log_analytics_name = "log-mytre"
static_web_storage = "stwebmytre"
```

The Azure TRE instance is initially deployed with an invalid self-signed SSL certificate. This certificate needs to be replaced with one valid for your configured domain name. To use a certificate from [Let's Encrypt](https://letsencrypt.org/), run the command:

```bash
make letsencrypt
```

!!! caution
    There are rate limits with Let's Encrypt, so this should not be run when not needed.

!!! info
    If you're using Codespaces, you'll encounter a bug when trying to run `make letsencrypt` where the incorrect IP will be whitelisted on the storage account and Codespaces won't be able to upload the test file due to a 403 error. The workaround until this is fixed is to temporarily disable the firewall on your `stweb{TRE_ID}` storage account before running the script, then re-enable afterwards.

## Validate the deployment

### Using curl

Use `curl` to make a simple request to the health endpoint of the API:

```bash
curl https://<azure_tre_fqdn>/api/health
```

The expected response is:

```json
{
  "services": [
    {
      "service": "Cosmos DB",
      "status": "OK",
      "message": ""
    },
    {
      "service": "Service Bus",
      "status": "OK",
      "message": ""
    },
    {
      "service": "Resource Processor",
      "status": "OK",
      "message": ""
    }
  ]
}
```

### Using the API docs

Open your browser and navigate to the `/api/docs` route of the API:  `https://<azure_tre_fqdn>/api/docs` and click `Try it out` on the operation of choice.

![Swagger UI](../../assets/quickstart_swaggerui.png)


## Using the DEPLOY_MODE variable

The `DEPLOY_MODE` variable allows you to control whether the deployment runs in 'plan' mode or 'apply' mode. In 'plan' mode, the terraform plan is generated and can be reviewed before applying. In 'apply' mode, the terraform plan is applied directly.

### Setting the DEPLOY_MODE variable

To set the `DEPLOY_MODE` variable, use the following commands:

```bash
export DEPLOY_MODE=plan
```

or

```bash
export DEPLOY_MODE=apply
```

### Example usage

To run the deployment in 'plan' mode:
=======
## Using the `DEPLOY_MODE` variable

To use the `DEPLOY_MODE` variable, follow these steps:

1. Set the `DEPLOY_MODE` variable to either `plan` or `apply` depending on your desired deployment mode.
2. Run the deployment command with the `DEPLOY_MODE` variable set.

Example:
```bash
export DEPLOY_MODE=plan
make all
```

To run the deployment in 'apply' mode:

```bash
export DEPLOY_MODE=apply
make all
```
=======
When `DEPLOY_MODE` is set to `plan`, the deployment script will execute the terraform plan without applying it, allowing you to review the changes before deciding to apply them. When `DEPLOY_MODE` is set to `apply`, the deployment script will execute the terraform plan and apply the changes automatically.


## Next steps

* [Configure Shared Services](configuring-shared-services.md)
* [Enable users to access the Azure TRE instance](../auth.md#enabling-users)
