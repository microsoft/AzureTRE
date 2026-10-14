# Configuring Shared Services

In general, a shared service should be installed by using the UI or API directly once its bundle has been registered on the system.

As part of this quickstart, you will need to install the Nexus shared service, as you will be subsequently deploying Guacamole VMs that depend on public package repositories to bootstrap. Due to the TRE's Firewall blocking public access, Nexus will proxy these package repositories and make them available within the TRE for the VMs to consume.

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

The bundle recovers a soft-deleted certificate during installation when the vault's retention policy still permits recovery.
An access or recovery failure stops installation. Inspect the operation before retrying; do not purge certificates as routine cleanup.

Once deployed, the certs service will use Letsencrypt to generate a certificate for the specified domain prefix followed by `-{TRE_ID}.{LOCATION}.cloudapp.azure.com`, so in our case, having entered `nexus`, this will be `nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com`, which will be the public domain for our Nexus service.

You can verify whether this has been successful by navigating to your core keyvault (`kv-{TRE_ID}`) and looking for a certificate called `nexus-ssl` (or whatever you called it).

### Certificate reuse and renewal

Certificate bundle `0.9.0` checks the configured certificate name in the core vault before requesting another certificate.
This behaviour applies to normal deployments and CI. It needs no extra vault or CI setting.

Install and `renew` reuse an enabled certificate when it has the exact requested DNS name, a trusted chain, a matching private key and more than 30 days before expiry.
The certificate remains at its existing name, such as `nexus-ssl`. The password secret and consumer references remain unchanged.
If no issued version exists, or an otherwise valid certificate is due for renewal, the bundle requests a certificate.
A lookup error, disabled version or invalid certificate stops the operation without another issuance attempt.

Terraform creates a temporary self-signed certificate before the script runs. On reinstallation, Terraform can recover earlier versions, then import the temporary certificate again.
The helper recognises that exact temporary certificate and checks the newest issued version under the same name.
It does not skip an invalid or disabled issued version to use an older one. An incomplete or ambiguous version history also stops reuse.
Certificate lookup has a three-minute deadline.

Uninstall removes the service infrastructure and soft-deletes the certificate and password under the existing vault policy.
Reinstallation can reuse recovered material until that policy removes it. Purged certificates cannot be reused.
Use the same hostname and certificate name for replacement. Run only one certificate lifecycle or dependent test suite per environment at a time.
The certificate-only test requires an environment without Nexus because removing its certificate dependency can interrupt Nexus.

The script validates newly issued material before import. After import, a retry can reuse the certificate if a later password or gateway update fails.
If issuance succeeds but import fails, there is no stored certificate to reuse. ACME errors still fail the operation; follow any retry time returned by the issuer.
On success or failure, the script removes temporary private files and attempts to stop its Application Gateway.
A failed stop also fails the operation. Cleanup preserves an earlier failure.

This uses the existing core-vault permissions. Identities that can read certificate secrets retain that access.
Certificate reuse does not add permission isolation. Review existing grants separately when tightening access.
Scheduled renewal, custom-domain configuration and distribution of updates to other services are separate capabilities.

#### Environments that used earlier draft bundles

Earlier drafts retained `tre-acme-` entries in the core vault or used a dedicated `kv-acme-{TRE_ID}` vault.
Version `0.9.0` reads the active certificate name. It does not read, move or delete those cache entries.
Confirm that the required certificate exists at its active name before retiring an earlier cache.
Review the Terraform plan before deploying code that removes the dedicated vault module, because it can delete that vault and related resources.
Handle old cache entries as separate cleanup. Do not purge them or delete active service certificates as part of that cleanup.

The bundle's `upgrade` action does not change infrastructure. Registering the new template alone does not update an installed bundle.
Verify the installed resource's bundle version before relying on the new reuse behaviour.

### Deploy Nexus

After verifying the certificate has been generated, you can deploy Nexus:

1. Run the below command in your terminal to build, publish and register the Nexus shared service bundle:

  ```cmd
  make shared_service_bundle BUNDLE=sonatype-nexus-vm
  ```

1. Navigate back to the TRE UI, and click *Create new* again within the Shared Services page.

1. Select the Nexus template then fill in the required details. The *SSL certificate name* should default to `nexus-ssl`, so there's no need to change it unless you gave it a different name in the previous step.

This will deploy the infrastructure required for Nexus, then start the service and configure it with the repository configurations located in the `./templates/shared_services/sonatype-nexus-vm/scripts/nexus_repos_config` folder. It will also set up HTTPS using the certificate you generated in the previous section, so proxies can be served at `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com`.

You can optionally go to the Nexus web interface by visiting `https://nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com/` in the jumpbox and signing in with the username `admin` and the password secret located in your core keyvault, with the key `nexus-admin-password`. Here you should be able to see all of the configured repositories and you can use the UI to manage settings etc.

Just bear in mind that if this service is redeployed any changes made in the Nexus UI won't be persisted.
If you wish to permanently add, alter or remove repositories, modify the JSON files within the `./nexus_repos_config` directory and upgrade the shared service.
On upgrade the updated configuration is copied to the existing Nexus VM and re-applied via the Nexus API, so the VM does not need to be recreated.
Note that deleting a JSON file does not remove the corresponding repository from a running Nexus instance; remove it via the Nexus UI or API as well.

You can view further information on the [Nexus shared service documentation](../../tre-templates/shared-services/nexus.md).

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

More info on the Gitea shared service is available in the [Gitea shared service documentation](../../tre-templates/shared-services/gitea.md).

## Next steps

* [Install Base Workspace](installing-base-workspace.md)
