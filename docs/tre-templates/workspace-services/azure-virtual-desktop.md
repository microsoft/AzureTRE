# Azure Virtual Desktop Service bundle

This service deploys Azure Virtual Desktop (AVD) with personal child-resource VMs or workspace-managed pooled, multi-session VMs. It includes private endpoints, start-on-connect, restricted device redirection, Entra authentication, and Log Analytics diagnostics.

## Limitations

| Area | What to expect |
| ---- | -------------- |
| One-way clipboard | Chosen at service creation. Bootstrap writes machine policy, restarts the VM, and verifies the boot/policy before registration. Test both directions before use. |
| Policy permissions | Standard users cannot normally change machine policy. Local administrators can; do not give researchers administrator access or VM administrator credentials. |
| Access removal | Group membership changes follow normal authorization propagation; removing TRE access does not terminate active sessions. Manage access through the workspace groups, not individual application assignments. |
| Multiple personal desktops | Each user resource is explicitly assigned to its owner. Its Connect link targets that VM, even when the owner has several desktops in the same pool. |

## Architecture

The service deploys an AVD host pool, workspace, desktop application group, private endpoints, and pooled session hosts when selected. Personal session hosts are child user resources.

The parent workspace's owners and researchers groups receive `Desktop Virtualization User` on the application group and `Virtual Machine User Login` on pooled VMs. No application-role or group-member discovery is used. Personal VMs are assigned to, and grant VM login only to, the child resource owner. Administrator login is not granted.

## Tenant prerequisites

Enable TRE `auto_workspace_group_creation` and provision the workspace groups first. The parent must expose non-empty `workspace_owners_group_id` and `workspace_researchers_group_id` outputs. Users, including TRE administrators, must belong to an entitled workspace group to see desktops; individual workspace-application assignments and personal VM ownership do not grant AVD application-group access.

An administrator must also enable tenant RDP authentication and review Conditional Access using [Microsoft's AVD SSO setup](https://learn.microsoft.com/azure/virtual-desktop/configure-single-sign-on). The bundle configures host-pool SSO but does not change tenant settings or Conditional Access.

Deployment permissions are normally provided by TRE setup:

- `auto_workspace_app_registration` makes `make auth` grant `Application.ReadWrite.All` and `Directory.Read.All`. Without optional pre-consent, restricted setups can instead grant `Application.Read.All` or equivalent access.
- The resource processor needs `User Access Administrator` on the workspace subscription. Core grants this on its subscription; configure it separately for cross-subscription workspaces.

For supported clients, images, and external identities, follow [AVD prerequisites](https://learn.microsoft.com/azure/virtual-desktop/prerequisites) and [authentication requirements](https://learn.microsoft.com/azure/virtual-desktop/authentication). Guests sign in with their home account, not the generated `#EXT#` UPN.

### Optional pre-consent

`enable_sso_preconsent` defaults off. When enabled at service creation, Terraform creates a dynamic group matching the service's Entra-joined host-name prefix and registers it with Windows Cloud Login. This hides the consent prompt but does not grant access or bypass authentication. Restrict Entra device creation and renaming so unrelated devices cannot match the rule.

The operation needs Graph `Application-RemoteDesktopConfig.ReadWrite.All` plus `Group.Create` or `Group.ReadWrite.All`; `Application.ReadWrite.All` is a broader alternative to the application permission.

`make auth` grants `Application.ReadWrite.All` with `auto_workspace_app_registration`, and separately grants `Group.ReadWrite.All` with `auto_workspace_group_creation`. Leave pre-consent disabled without these grants, or [configure trusted device groups separately](https://learn.microsoft.com/azure/virtual-desktop/configure-single-sign-on#hide-the-consent-prompt-dialog).

Each service uses one trusted-group slot, propagation can delay the effect, and the first connection may still prompt. Test sign-in with a non-admin user and a B2B guest.

### Licensing

The bundle does not verify entitlement. Review [AVD licensing](https://learn.microsoft.com/azure/virtual-desktop/licensing), [group assignment](https://learn.microsoft.com/entra/identity/enterprise-apps/assign-user-or-group-access-portal), and [dynamic group licensing](https://learn.microsoft.com/entra/identity/users/groups-dynamic-membership).

## Configuration Options

| Property | Options | Description |
| -------- | ------- | ----------- |
| `host_pool_type` | `Personal`/`Pooled` (Default: `Personal`) | Select personal child VMs or workspace-managed pooled VMs |
| `enable_sso_preconsent` | `true`/`false` (Default: `false`) | Automate a service-owned dynamic device group for pre-consent; consider licensing and optional Graph write permissions |
| `maximum_sessions` | 1-50 (Default: 10) | Maximum concurrent sessions on each pooled host |
| `pooled_session_host_count` | 1-10 (Default: 1) | Updateable number of multi-session hosts in a pooled deployment |
| `pooled_os_image` | Windows 11 25H2/24H2 Multi-Session (Default: 25H2) | Image selected at creation; pooled hosts use Premium SSD OS disks |
| `pooled_vm_size` | Supported `Standard_D*s_v6` size | VM size used by pooled session hosts |
| `enable_clipboard` | `true`/`false` (Default: `false`) | Enable clipboard redirection between session and client |
| `clipboard_transfer_direction` | `disabled`/`client_to_session`/`session_to_client`/`both` (Default: `disabled`) | Direction of allowed clipboard transfers |

The pooled-only settings are shown only for pooled host pools. Host-pool type is fixed at service creation (`updateable: false`). Multiple personal desktop assignment cannot be disabled once enabled. Before reducing the pooled host count, drain the hosts being removed (highest numbered hosts first) and end their active sessions; scaling down deletes those VMs and their disks.

### Clipboard and redirection

Clipboard defaults off. For **client-to-desktop only**, set `enable_clipboard = true` and `clipboard_transfer_direction = client_to_session`. This allows copying into the desktop and blocks copying back once host policy is effective.

One-way control uses Windows machine policies (`SCClipLevel` and `CSClipLevel`), which client preferences cannot override. VM administrators can alter these controls. See [clipboard transfer direction](https://learn.microsoft.com/en-us/azure/virtual-desktop/clipboard-transfer-direction-data-types).

## Firewall Rules

The following firewall rules are opened for the workspace when this service is deployed:

Network service tags:

- WindowsVirtualDesktop
- AzureActiveDirectory

HTTPS application rules for AVD platform traffic:

- `catalogartifact.azureedge.net`
- `mrsglobalsteus2prod.blob.core.windows.net`
- `wvdportalstorageblob.blob.core.windows.net`
- `*.windows.cloud.microsoft` and `*.windows.static.microsoft`
- `gcs.prod.monitoring.core.windows.net`
- `*.prod.warm.ingest.monitor.core.windows.net`

The bundle also allows the documented certificate endpoints over HTTP, Windows activation over TCP 1688 to `20.118.99.224` and `40.83.235.53`, and UDP relay at `51.5.0.0/16:3478`.
The activation addresses are Microsoft's [documented Azure public-cloud KMS endpoints](https://learn.microsoft.com/troubleshoot/azure/virtual-machines/windows/windows-activation-stopped-working#cause-2-the-firewall-is-blocking-access-to-the-kms-server).
Review these addresses when Microsoft changes its endpoints; sovereign clouds require their corresponding KMS addresses.

The activation rule uses IP addresses so it works with Azure Firewall Basic, Standard, and Premium without DNS proxy. This bundle does not require changing client DNS settings or disabling TRE's optional DNS security policy.
Base workspace 2.9.0 provides the NSG paths, workspace DNS link, and workspace-owned Terraform role assignment granting the resource processor Storage Blob Data Contributor. Core 0.17.0 provides the Windows cloud DNS suffixes and the shared AVD private DNS zone linked to the core network. Deploy those components before AVD. The firewall still controls external destinations.

See [Protect Azure Virtual Desktop with Azure Firewall](https://learn.microsoft.com/azure/firewall/protect-azure-virtual-desktop) for platform requirements.

## Bootstrap integrity

Both bundles pin Microsoft's portal configuration archive `Configuration_1.0.03519.1433.zip` and verify its SHA-256 digest during build and on the session host. The archive still uses PowerShell DSC. Pinning provides integrity and reproducibility, not a security audit of elevated code.

Before bootstrap, both bundles reuse a registration token with at least four hours remaining or generate a new 24-hour token. A renewable per-pool storage lease serializes renewal, and Key Vault passes the token to the host deployment without printing it. Existing registered hosts do not need this token. Do not rotate registration credentials manually during deployment.

Uninstall and pooled scale-down remove session-host registrations before VM deletion; missing registrations are tolerated.

## Prerequisites

- [Base workspace 2.9.0 or later](../workspaces/base.md) and core 0.17.0 or later

## Personal desktops

For Personal pools, owners and researchers can create child resources that deploy one Entra-joined VM, register it with the parent pool, and assign it to the resource owner. The child supports image, VM size, shared storage, and shutdown settings. Pooled pools create their hosts in the parent service and do not use this child resource.

### Shared storage compatibility

Shared storage defaults off. It mounts the workspace file share with a storage-account key, which has broader access than an individual identity. Leave it disabled where key-based access is prohibited.

## Connecting to Azure Virtual Desktop

Use **Connect** on a pooled workspace service or personal child resource. Pooled links open the published desktop; personal links target the assigned VM directly. Personal parent services do not expose a link.

Windows App groups desktops by the TRE workspace name. Published desktops use the service name, and personal desktops use the child resource's display name. Give personal resources distinct names to distinguish them in the device list. Labels are applied during bundle install or upgrade; after renaming the TRE workspace, upgrade its AVD services to refresh the group heading.

The service and personal resource bundles are version 1.0.0. Azure resource names use the CAF prefixes `vdpool`, `vdws`, and `vdag`. Each personal `connection_uri` includes the AVD workspace and published-desktop object IDs, the authentication tenant ID, and `endpointId` from the session host's `properties.objectId` (not the Azure VM ID). A login hint is omitted so guests can choose their home account.

Clients: [Windows App web](https://windows.cloud.microsoft), [Windows](https://apps.microsoft.com/detail/9n1f85v9t8bn), and [macOS](https://aka.ms/WindowsAppMac). See the [AVD documentation](https://learn.microsoft.com/en-us/azure/virtual-desktop/) for other supported clients.
