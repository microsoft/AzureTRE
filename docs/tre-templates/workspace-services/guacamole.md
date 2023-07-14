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
