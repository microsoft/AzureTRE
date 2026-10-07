---
name: tre-bundle-development
description: Checks Azure TRE bundle contracts, network and identity boundaries, and install, upgrade and uninstall behaviour. Use when you change or review Porter/Terraform resource bundles under templates/.
---

# Azure TRE bundle development

## Trace the bundle contract

Start with the changed bundle's `porter.yaml`, `template_schema.json`, `parameters.json`, `Dockerfile.tmpl` and `terraform/` directory where present. Inspect `porter-build-context.env` and referenced files when the bundle uses shared build inputs.

Use [template authoring](../../../docs/tre-workspace-authors/authoring-workspace-templates.md) for the supported schema contract and [resource processor](../../../docs/tre-developers/resource-processor.md) for execution context.

1. Identify the resource type and parent resources. User-resource bundles can be nested under a workspace-service bundle.
2. Trace each changed user-facing property from its schema through Porter parameters to Terraform variables or scripts.
3. Check defaults, types, required values, substitutions and Azure TRE annotations such as `sensitive`, `readOnly` and `updateable`.
4. Check `parameters.json` against the Porter parameter set. Internal deployment parameters do not all belong in the user-facing schema.
5. Trace changed outputs back to their consumers, including API substitutions, connection details and dependent pipeline steps.

## Check network and identity boundaries

Apply the [security baseline](../../../AGENTS.md#security-baseline) and inspect the effective configuration for every changed network or identity setting:

1. List added or widened outbound hosts, service tags and firewall rules, including their source networks, protocols and ports.
2. Check whether an allowed destination can receive research data in another subscription, tenant or externally controlled account, bypassing Airlock.
3. Inspect public network access, private endpoints, DNS and routing for exposure or paths around the intended hub-and-spoke boundaries.
4. Trace managed identities and RBAC assignments to their consumers. Check roles, assignment scopes and inherited grants for excessive access.
5. Check install, upgrade and uninstall for temporary access changes and restoration, including failure paths. Record any required exception and its justification.

An allowed FQDN is not a tenant or subscription boundary. For example, `management.azure.com` serves ARM operations across subscriptions. A researcher with external credentials and permissions could use that allowed host to send data outside the TRE. Assess the endpoint's capabilities and effective controls, not just its hostname.

See [Azure Firewall FQDN filtering](https://learn.microsoft.com/en-us/azure/firewall/domain-filtering-overview) and [ARM Run Command requests](https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/run-command) for the filtering and request models.

## Check every affected lifecycle action

For install, upgrade and uninstall, identify where each changed input gets its value. A new required Terraform variable can break uninstall even when install passes. Pass the input for every action that needs it, or provide a default whose meaning is valid for those actions.

Consider existing installations as well as new deployments. Review state addresses, replacement plans and data retention before changing resource identity or Terraform lifecycle rules. Treat unexpected destruction or required manual migration as a compatibility concern when choosing the version.

Template validation is not full JSON Schema conformance. Read the supported-keyword and dialect rules in the authoring guide. A schema that passes a standalone validator can still fail API registration, PATCH validation or UI form rendering. Check the affected production path when changing schema behaviour.

## Select validation

Use the Terraform and Porter versions pinned in [.devcontainer/Dockerfile](../../../.devcontainer/Dockerfile). The [build-validation workflow](../../../.github/workflows/build_validation_develop.yml) defines the Terraform checks used by CI.

From the repository root, these commands illustrate checks for Guacamole. Substitute the changed Terraform directory:

```bash
terraform fmt -check -recursive templates/workspace_services/guacamole/terraform
terraform -chdir=templates/workspace_services/guacamole/terraform init -backend=false
terraform -chdir=templates/workspace_services/guacamole/terraform validate
```

Initialisation downloads providers and modules. It does not apply resources. A successful validation does not test input values supplied by Porter or the live lifecycle.

For a bundle build, inspect [porter_build_bundle.sh](../../../devops/scripts/porter_build_bundle.sh) and the [Dockerfile build workflow](../../../.github/workflows/build_all_dockerfiles.yml). Preserve named build contexts and shared runtime-image dependencies. Run the build for the affected bundle using the configured development environment.

The root `make bundle-build DIR=<bundle-directory>` target also bootstraps Azure configuration and can change ACR access. `make bundle-check-params DIR=<bundle-directory>` needs a built bundle and checks `parameters.json` against Porter, not against `template_schema.json`. Inspect these [Makefile targets](../../../Makefile) before running them within the authorised task.

When live validation is available and authorised, exercise the changed install, upgrade and uninstall paths. Record the bundle versions, tested input values and resulting operations. Report untested lifecycle paths explicitly.

## Release and review

Apply [component version and changelog requirements](../../../AGENTS.md#contribution-requirements). Check separately versioned container images if their sources change. Ensure examples and parameter files remain consistent with the final behaviour.

Use the [code-review skill](../tre-code-review/SKILL.md) to recommend the appropriate PR checks. Formatting, Terraform validation and a successful image build do not establish a successful bundle deployment or upgrade.
