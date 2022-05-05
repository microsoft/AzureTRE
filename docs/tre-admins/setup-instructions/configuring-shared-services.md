# Configuring Shared Services

Complete the configuration of the shared services (Nexus and Gitea) from inside of the TRE environment.

## Configure Nexus

Before deploying the Nexus shared service, you need to make sure that it will have access to a certificate to configure serving secure proxies. By default, the Nexus service will serve proxies from `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/`, and thus it requires a certificate that validates ownership of this domain to use for SSL.

You can use the Certs Shared Service to set one up by following these steps:

1. Run the below commands in your terminal to build, publish and register the certs bundle:

  ```cmd
  make bundle-build DIR=./templates/shared_services/certs
  make bundle-publish DIR=./templates/shared_services/certs
  make bundle-register DIR=./templates/shared_services/certs BUNDLE_TYPE=shared_service
  ```

1. Navigate to the Swagger UI for your TRE API at `https://<azure_tre_fqdn>/api/docs`, and authenticate if you haven't already by clicking `Authorize`.

1. Click `Try it out` on the `POST` `/api/shared-services` operation, and paste the following to deploy the certs service:

  ```json
  {
    "templateName": "tre-shared-service-certs",
    "properties": {
      "display_name": "Nexus cert",
      "description": "Generate/renew ssl cert for Nexus shared service",
      "domain_prefix": "nexus",
      "cert_name": "nexus-ssl"
    }
  }
  ```

1. Once the shared service has been deployed (which you can check by querying the `/api/shared-services/operations` method), copy its `resource_id`, then find the `POST` operation for `/api/shared-services/{shared_service_id}/invoke_action`, click `Try it out` and paste in the resource id into the `shared_service_id` field, and enter `generate` into the `action` field, then click `Execute`.

This will invoke the certs service to use Letsencrypt to generate a certificate for the specified domain prefix followed by `-{TRE_ID}.{LOCATION}.cloudapp.azure.com`, so in our case, having entered `nexus`, this will be `nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com`, which will be the public domain for our Nexus service.

Once this has completed, you can verify its success either from the operation output, or by navigating to your core keyvault (`kv-{TRE_ID}`) and looking for a certificate called `nexus-ssl`.

After verifying the certificate has been generated, you can deploy Nexus:

1. Run the below commands in your terminal to build, publish and register the Nexus shared service bundle:

  ```cmd
  make bundle-build DIR=./templates/shared_services/sonatype-nexus
  make bundle-publish DIR=./templates/shared_services/sonatype-nexus
  make bundle-register DIR=./templates/shared_services/sonatype-nexus BUNDLE_TYPE=shared_service
  ```

1. Navigate to the Swagger UI for your TRE API at `https://<azure_tre_fqdn>/api/docs`, and authenticate if you haven't already by clicking `Authorize`.

1. Click `Try it out` on the `POST` `/api/shared-services` operation, and paste the following to deploy the Nexus shared service:

  ```json
  {
    "templateName": "tre-shared-service-nexus",
    "properties": {
      "display_name": "Nexus",
      "description": "Proxy public repositories with Nexus"
    }
  }
  ```

This will deploy the infrastructure required for Nexus, then start the service and configure it with the repository configurations located in the `./templates/shared_services/sonatype-nexus/scripts/nexus_repos_config` folder. It will also set up HTTPS using the certificate you generated in the previous section, so proxies can be served at `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com`.

You can optionally go to the Nexus web interface by visiting `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/` in the jumpbox and signing in with the username `admin` and the password secret located in your core keyvault, with the key `nexus-admin-password`. Here you should be able to see all of the configured repositories and you can use the UI to manage settings etc.

Just bear in mind that if this service is redeployed any changes in the UI won't be persisted. If you wish to add new repositories or alter existing ones, use the JSON files within the `./nexus_repos_config` directory.

## Configure Gitea repositories

Note : This is a Gitea *shared service* which will be accessible from all workspaces intended for mirroring external Git repositories. A Gitea *workspace service* can also be deployed per workspace to enable Gitea to be used within a specific workspace.

By default, this Gitea instance does not have any repositories configured. You can add repositories to Gitea either by using the command line or by using the Gitea web interface.


### Command Line
Make sure you run the following commands using git bash and set your current directory as C:/AzureTRE.

1. On the jumbox, run:
```./scripts/gitea_migrate_repo.sh -t <tre_id> -g <URL_of_github_repo_to_migrate>```
1. If you have issues with token or token doesn't work, you can reset the token by setting it's value to null in Key Vault:
```az keyvault secret set --name gitea-<tre-id>-admin-token --vault-name kv-<tre-id> --value null```

### Gitea Web Interface

1. on the jumbox, open Edge and go to:
```https://gitea-<TRE_ID>.azurewebsites.net/```
1. Authenticate yourself using username ```giteaadmin``` and the secret ```<gitea-TRE_ID-administrator-password>``` stored in the keyvault,
1. Add the repository of your choice

### Verify can access the mirrored repository

From a virtual machine within a workspace:
- Command line: ```git clone https://gitea-<TRE_ID>.azurewebsites.net/giteaadmin/<NameOfrepository>```
- Gitea Web Interface: ```https://gitea-<TRE_ID>.azurewebsites.net/```
