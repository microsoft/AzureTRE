# Guacamole Service bundle

See: [https://guacamole.apache.org/](https://guacamole.apache.org/)

## Firewall Rules

Please be aware that the following Firewall rules are opened for the workspace when this service is deployed:

Service Tags:

- AzureActiveDirectory

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)

## Guacamole Workspace Service Configuration

When deploying a Guacamole service into a workspace the following properties need to be configured.

### Optional Properties

| Property | Options | Description |
| -------- | ------- | ----------- |
| `guac_disable_copy` | `true`/`false` (Default: `true`) | Disable Copy functionality |
| `guac_disable_paste` | `true`/`false` (Default: `false`) | Disable Paste functionality" |
| `guac_enable_drive` | `true`/`false` (Default: `true`) | Enable mounted drive |
| `guac_disable_download` | `true`/`false` (Default: `true`) | Disable files download |
| `guac_disable_upload` | `true`/`false` (Default: `true`) | Disable files upload |
| `is_exposed_externally` | `true`/`false` (Default: `true`) | Is the Guacamole service exposed outside of the vnet |

## Notes

### VM tooling and bootstrap time

The Windows and Linux VM user resources provided with Guacamole install their
tooling (for example Azure CLI, Visual Studio Code, Azure Storage Explorer and
data science packages) via a bootstrap script that runs at deploy time. This
download-and-install step typically adds **10-15 minutes (or more)** to VM
provisioning, depending on how many tools are selected.

To provision VMs faster and to avoid transient issues downloading and installing
packages, we recommend using a custom VM image with the tooling pre-installed.
The included user resource templates that rely on bootstrap scripts should only
be used for trial/demonstration purposes. More info can be found in the
[custom templates documentation](../user-resources/custom.md).

### Command trace in earlier versions

Before `tre-service-guacamole` 0.14.8, the Guacamole server wrote the start
command of oauth2-proxy to the console log of its web app. This command has the
cookie secret of oauth2-proxy, and the web app sends the log to the Log
Analytics workspace of the TRE core. The server makes a new cookie secret at
each start and keeps it only in memory. The upgrade to 0.14.8 restarts the
server, so after the upgrade the old value in Log Analytics has no use.

Before `tre-service-guacamole-linuxvm` 1.4.10, the setup script of the Linux VM
wrote its commands to the cloud-init output log `/var/log/cloud-init-output.log`
on the VM. Some of these commands have the key of the workspace storage
account, which the VM uses for the workspace file share. An upgrade does not
change an existing VM, so its log keeps the key. The VM also keeps the key in
the credential file of the share in `/etc/smbcredentials` and in its cloud-init
user data, so a change of the log does not remove the key from the VM.

If the people who can sign in to such a VM must not keep the key, rotate the
key of the workspace storage account. After a rotation, the share mount of each
existing VM fails until the VM gets the new key.
