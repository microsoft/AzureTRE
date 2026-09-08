# Guacamole ACI Desktop PoC

Ubuntu 22.04 container desktop with XFCE, Microsoft Edge, XRDP, Visual Studio
Code, Python/Jupyter, R/RStudio, Azure CLI, Storage Explorer, and Git. Docker and
nested container runtimes are not supported.

The software is installed in independently cached image layers at build time.
Container startup only applies deployment-specific configuration and starts the
desktop services, avoiding the lengthy post-provision installation used by a VM.

## Build and register

From the repository root, build and publish the runtime image and bundle using
the standard scripts:

```bash
cd templates/workspace_services/guacamole/user_resources/guacamole-azure-container
ACR_NAME=<acr-name> FULL_IMAGE_NAME_PREFIX=<acr-name>.azurecr.io \
  ../../../../../devops/scripts/bundle_runtime_image_push.sh
../../../../../devops/scripts/porter_build_bundle.sh
porter publish --reference <acr-name>.azurecr.io/tre-service-guacamole-container:v0.3.2
```

The runtime image version is defined in `image/version.txt`. Public vendor
repositories are used to construct the image; runtime apt, Python, and R package
sources use the workspace's Nexus service.

## Deployment

Deploy or upgrade `tre-service-guacamole` first. Its pipeline reserves an ACI
address range on the workspace and creates a delegated subnet. All container
desktops under that Guacamole service share the subnet.

Create a `tre-service-guacamole-container` user resource and select one of the
available CPU and memory profiles. The container receives a private IP and
exposes only RDP port 3389. A unique desktop password is stored in the workspace
Key Vault. A user-assigned identity grants access to pull the runtime image, and
the interactive desktop runs as the non-root `researcher` account.

Shared storage defaults to disabled because ACI's native Azure Files mount uses
the storage account key, while Azure TRE disables Shared Key authorization by
default. The container's home directory and browser profile are ephemeral.

The resource provides `start` and `stop` actions. Stopping the group deallocates
compute, but starting it creates a fresh container and discards writable
container state. Its private IP can change after a start or replacement.

## Performance

The scenario in issue #4311 reports 15 minutes or more before a review VM is
usable. In a deployed test, this desktop's uncached 2.14 GiB image pull took
approximately 2 minutes 32 seconds and the container started about 15 seconds
later. Warm starts can reuse cached layers, but timing depends on ACI capacity,
regional image caching, and network throughput.

## Verification and limits

The runtime image and bundle were deployed end to end. Guacamole login, XFCE,
Microsoft Edge first launch, the RDP listener, and the packaged data science
tools were verified on ACI. The image smoke test also checks that Docker is not
installed and renders a page with non-root headless Edge.

This remains a proof of concept requiring production validation. In particular:

- Docker and nested container workloads are not supported.
- The operating-system filesystem and user profile are ephemeral.
- Cold image pulls can still take several minutes.
- Shared storage requires an explicitly approved policy permitting Shared Key.
- The subnet retains the workspace NSG and firewall route; this template does
  not add a NAT gateway or unrestricted outbound access.
- Delete container desktops before deleting their parent Guacamole service.