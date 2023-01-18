# Configuring Shared Services

In general, a shared service should be installed by using the UI or API directly once its bundle has been registered on the system.

As part of this quickstart, you will need to install the Nexus shared service, as you will be subsequently deploying Guacamole VMs that depend on public package respositories to bootstrap. Due to the TRE's Firewall blocking public access, Nexus will proxy these package repositories and make them available within the TRE for the VMs to consume.

## Deploy & configure Nexus service

!!! caution
    Before deploying the Nexus service, you will need workspaces of version `0.3.2` or above due to a dependency on a DNS zone link for the workspace(s) to connect to the Nexus VM.

Before deploying the Nexus shared service, you need to make sure that it will have access to a certificate to configure serving secure proxies. By default, the Nexus service will serve proxies from `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/`, and thus it requires a certificate that validates ownership of this domain to use for SSL.

You can use the Certs Shared Service to set one up by following these steps:

1. Run the below command in your terminal to build, publish and register the certs bundle:

  ```cmd
  make shared_service_bundle BUNDLE=certs
  ```

2. Navigate to the TRE UI, click on Shared Services in the navigation menu and click *Create new*.

3. Select the Certs template, then fill in the required details. *Domain prefix* should be set to `nexus` and *Cert name* should be `nexus-ssl`.

!!! caution
    If you have KeyVault Purge Protection enabled and are re-deploying your environment using the same `cert_name`, you may encounter this: `Status=409 Code=\"Conflict\" Message=\"Certificate nexus-ssl is currently in a deleted but recoverable state`. You need to either manually recover the certificate or purge it before redeploying.

Once deployed, the certs service will use Letsencrypt to generate a certificate for the specified domain prefix followed by `-{TRE_ID}.{LOCATION}.cloudapp.azure.com`, so in our case, having entered `nexus`, this will be `nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com`, which will be the public domain for our Nexus service.

You can verify whether this has been successful by navigating to your core keyvault (`kv-{TRE_ID}`) and looking for a certificate called `nexus-ssl` (or whatever you called it).

After verifying the certificate has been generated, you can deploy Nexus:

1. Run the below command in your terminal to build, publish and register the Nexus shared service bundle:

  ```cmd
  make shared_service_bundle BUNDLE=sonatype-nexus-vm
  ```

1. Navigate back to the TRE UI, and click *Create new* again within the Shared Services page.

1. Select the Nexus template then fill in the required details. The *SSL certificate name* should default to `nexus-ssl`, so there's no need to change it unless you gave it a different name in the previous step.

This will deploy the infrastructure required for Nexus, then start the service and configure it with the repository configurations located in the `./templates/shared_services/sonatype-nexus-vm/scripts/nexus_repos_config` folder. It will also set up HTTPS using the certificate you generated in the previous section, so proxies can be served at `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com`.

You can optionally go to the Nexus web interface by visiting `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/` in the jumpbox and signing in with the username `admin` and the password secret located in your core keyvault, with the key `nexus-admin-password`. Here you should be able to see all of the configured repositories and you can use the UI to manage settings etc.

Just bear in mind that if this service is redeployed any changes made in the Nexus UI won't be persisted. If you wish to permanently add new repositories or alter existing ones, modify the JSON files within the `./nexus_repos_config` directory and redeploy.

You can view further information on the Nexus shared service [here](../../tre-templates/shared-services/nexus.md).

## (Optional) Install Gitea and configure repositories

Gitea allows you to mirror Git repositories to make them available within the TRE. This is optional as part of this quickstart.

Note : This is a Gitea *shared service* which will be accessible from all workspaces intended for mirroring external Git repositories. A Gitea *workspace service* can also be deployed per workspace to enable Gitea to be used within a specific workspace.

To install Gitea, first register the template:

```cmd
  make shared_service_bundle BUNDLE=gitea
```

You can then install via the TRE UI in the same way you did for the Nexus bundle.

By default, this Gitea instance does not have any repositories configured. You can add repositories to Gitea either by using the command line or by using the Gitea web interface.

### Command Line

Make sure you run the following commands using git bash and set your current directory as C:/AzureTRE.

1. On the jumbox, run:
```./templates/workspace_services/gitea/gitea_migrate_repo.sh -t <tre_id> -g <URL_of_github_repo_to_migrate>```
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

More info on the Gitea shared service is available [here](../../tre-templates/shared-services/gitea.md).

## Next steps

* [Install Base Workspace](installing-base-workspace.md)
