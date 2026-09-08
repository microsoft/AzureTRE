# Guacamole Container Desktop user resource

The Guacamole Container Desktop is an Ubuntu 22.04 research desktop that runs
in Azure Container Instances (ACI) and is accessed through the workspace's
[Guacamole service](../workspace-services/guacamole.md). It provides XFCE,
Microsoft Edge, Visual Studio Code, Python and Jupyter, R and RStudio, Azure CLI,
Azure Storage Explorer, and Git.

Unlike the Guacamole Linux VM, the container desktop does not provide Docker,
a nested container runtime, systemd, or a persistent operating-system disk.
The interactive session runs as the non-root `researcher` user.

## Prerequisites

- [A base workspace bundle installed](../workspaces/base.md)
- [A Guacamole workspace service bundle installed](../workspace-services/guacamole.md)
- [A Nexus shared service deployed](../shared-services/nexus.md)
- A Guacamole workspace service version that provides the delegated ACI subnet

## Deployment

Create a **Linux Container Desktop** beneath the Guacamole workspace service.
The container receives a private address in the workspace virtual network and
exposes RDP only within that network. Guacamole retrieves the generated desktop
credentials from the workspace Key Vault.

The desktop software is installed when the runtime image is built, rather than
when the user resource is deployed. At container startup, the entrypoint applies
the generated desktop password, configures workspace-specific Nexus package
sources, creates the XRDP certificate, and starts DBus and XRDP. A first-time
ACI image pull can still take several minutes because the desktop image is
large.

Public vendor repositories are used to construct the runtime image. After
startup, apt, Python, and R package sources point to the workspace's Nexus
service.

### Compute size

Select one of the following compute profiles when creating or updating the
desktop:

| Profile | vCPU | Memory |
| ------- | ---- | ------ |
| 2 CPU \| 4GB RAM | 2 | 4 GB |
| 2 CPU \| 8GB RAM | 2 | 8 GB |
| 4 CPU \| 16GB RAM | 4 | 16 GB |

The default is **2 CPU | 8GB RAM**. ACI cannot resize a running container group
in place. Updating the compute profile replaces the container group and discards
its ephemeral filesystem.

## Starting and stopping

Use the **Start** and **Stop** actions on the user resource in Azure TRE. Stop
terminates the running container and deallocates its compute resources. Start
creates a new container deployment from the same configuration and image.

ACI does not preserve container state across a stop and start. Files in the
container's writable filesystem, including the researcher's home directory,
browser profile, downloads, and packages installed interactively, are discarded.
The user-resource definition, generated desktop password, managed identity, and
Terraform state remain. Data on an attached Azure Files share also remains.

The private IP address can change after a start or restart. The first start may
also need to pull the desktop image and can take several minutes.

ACI vCPU and memory billing starts when Azure begins pulling the image and stops
when the entire container group reaches the stopped state. Costs for other TRE
resources, container-registry storage, logging, networking, and any Azure Files
storage continue independently. See [Manually stop or start containers in Azure
Container Instances](https://learn.microsoft.com/azure/container-instances/container-instances-stop-start)
and the [Azure Container Instances pricing FAQ](https://learn.microsoft.com/azure/container-instances/container-instances-faq#when-does-the-meter-start-running).

## Shared storage

Shared storage is disabled by default. When enabled, ACI attempts to mount the
workspace's `vm-shared-storage` Azure Files share at
`/fileshares/vm-shared-storage` and creates `/vm-shared-storage` as a
compatibility link.

ACI's native Azure Files volume uses the storage account key. The mount cannot
succeed when the workspace storage account has Shared Key authorization
disabled, which is the standard Azure TRE security posture. In that case Azure
leaves the container group in `Creating` and reports
`FailedMountAzureFileVolume`; the container never starts.

Do not enable Shared Key authorization solely to deploy this user resource.
Leave shared storage disabled unless the TRE deployment has an explicitly
approved storage policy that supports ACI's key-based Azure Files mount. Without
a mounted share, the home directory and browser profile are ephemeral and data
is lost when the container is replaced or deleted.

## Limitations

- This template is a proof of concept and requires production validation.
- Docker and nested container workloads are not supported.
- The operating-system disk and user profile are ephemeral.
- Cold image pulls can make initial deployment substantially slower than warm
  starts.
- Larger compute profiles can be subject to regional ACI capacity and
  subscription quota limits.
- Delete container desktops before deleting their parent Guacamole service.
