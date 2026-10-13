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

!!! caution
    If you have KeyVault Purge Protection enabled and are re-deploying your environment using the same `cert_name`, you may encounter this: `Status=409 Code=\"Conflict\" Message=\"Certificate nexus-ssl is currently in a deleted but recoverable state`. You need to either manually recover the certificate or purge it before redeploying.

Once deployed, the certs service will use Letsencrypt to generate a certificate for the specified domain prefix followed by `-{TRE_ID}.{LOCATION}.cloudapp.azure.com`, so in our case, having entered `nexus`, this will be `nexus-{TRE_ID}.{LOCATION}.cloudapp.azure.com`, which will be the public domain for our Nexus service.

You can verify whether this has been successful by navigating to your core keyvault (`kv-{TRE_ID}`) and looking for a certificate called `nexus-ssl` (or whatever you called it).

### Certificate reuse and renewal

Certificate bundle `0.8.0` disables retention by default. Normal installs and `renew` actions request a certificate and publish the active certificate in the core vault.
The certificate script attempts to stop its Application Gateway after success or failure. A failed stop also fails the operation.

CI validation can reuse certificates to avoid repeated issuance when tests replace a service.
The PR, branch and main validation workflows explicitly set `enableCiCertificateCache` to `true`.
Other callers of the reusable workflow default to `false`.
The input sets the core Terraform variable `enable_ci_certificate_cache`, which also defaults to `false`.
It requires a CI Git reference and the VMSS Porter resource processor.

| Setting | Normal deployment | CI with retention enabled |
| --- | --- | --- |
| Retained material | None created | One hostname certificate in `kv-acme-{TRE_ID}` |
| Active certificate and password | Core vault, `kv-{TRE_ID}` | Core vault, `kv-{TRE_ID}` |
| Cache network access | No cache vault | Private endpoint in the shared subnet, with public access disabled |
| Cache roles created by TRE | None | Certificates Officer and Secrets User for the resource processor, Administrator for the CI deployer |
| Cache lifetime | Not applicable | Survives certificate service uninstall, until the CI core is removed or retention is disabled |

The cache vault grants no access to the API, Nexus, Gitea or Application Gateway identities.
Subscription and resource-group permissions still apply through Azure RBAC inheritance. Review those grants when configuring the CI environment.
Cache access is recorded in the TRE Log Analytics workspace.
Core deployment supplies the internal `certificate_cache_vault_name` bundle parameter. An empty value disables retention.
The script rejects the core vault as a cache destination.

Install and `renew` reuse a retained certificate only when more than 30 days remain before expiry.
The bundle verifies ownership, public trust, the exact DNS name and the private key before reuse.
It requests a certificate when no cache entry exists or renewal is due.
A vault lookup, ownership or certificate validation failure stops the operation without another issuance attempt.

Each cache entry is named `tre-acme-<SHA-256 of the lowercase hostname>` and has `tre-cache=certificate-v1` and `fqdn` tags.
It includes an exportable private key. Names starting with `tre-acme-` are reserved for these entries.
Uninstall removes the active service certificate and infrastructure, but preserves the CI cache for later installs.
Removing the CI core or disabling retention deletes the cache vault under its soft-delete and purge-protection policy.
The cache uses the core setting `kv_purge_protection_enabled`, which defaults to `true`.

If an administrator disables or deletes a cache entry, investigate that change before enabling or recovering it.
Do not remove the cache to bypass an issuance limit. Compromised certificates require revocation and replacement through the normal incident procedure.
The cache starts with the first successful issuance. It does not adopt certificates from other vaults or service aliases.
An ACME rate-limit response still fails the operation. Follow the retry time in that response.
Run only one certificate lifecycle or dependent test suite per environment at a time.

#### Environments that used earlier draft bundles

Draft versions `0.7.15` and `0.7.16` stored hostname caches in the core vault.
Version `0.8.0` does not read, move or delete those entries automatically. Upgrading alone does not remove the earlier retained keys.

1. List the `tre-acme-` certificates in `kv-{TRE_ID}`.
2. Confirm each entry's `tre-cache=certificate-v1` and `fqdn` tags before removing it.
3. Soft-delete the confirmed cache certificates. Keep the active service aliases, such as `nexus-ssl`.
4. Check inherited access and confirm that core-vault readers can no longer download those cache secrets.

Azure retains deleted objects under the vault's recovery policy. Do not purge them as part of routine cleanup.
A later CI install must issue its first certificate into the new vault, subject to the ACME issuance limits.

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
