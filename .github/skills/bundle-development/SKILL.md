---
name: bundle-development
description: Checks Porter, Terraform, schema and parameter consistency across install, upgrade and uninstall for Azure TRE resource bundles. Use when you change or review files under templates/.
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

Use the [code-review skill](../code-review/SKILL.md) to recommend the appropriate PR checks. Formatting, Terraform validation and a successful image build do not establish a successful bundle deployment or upgrade.
