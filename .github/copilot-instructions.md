# GitHub Copilot Instructions for Azure TRE

This file provides context and guidance for GitHub Copilot when working with the Azure Trusted Research Environment (Azure TRE) project.

## Project Overview

Azure TRE is an accelerator to assist Microsoft customers and partners who want to build out Trusted Research Environments on Azure. It enables authorized users to deploy and configure secure workspaces and researcher tooling without a dependency on IT teams.

Trusted Research Environments (TREs) enable organizations to provide research and development (R&D) teams secure access to data alongside tooling to ensure productivity while keeping security controls in place.

Core features include:
- Self-service workspace management for TRE administrators
- Self-service provisioning of R&D tooling for R&D teams
- Package and repository mirroring
- Extensible architecture with custom service templates
- Microsoft Entra ID integration
- Airlock for import and export
- Cost reporting

## Primary Technologies

Azure TRE uses the following key technologies:

- **Infrastructure as Code**:
  - Terraform for infrastructure provisioning
  - Porter/CNAB for bundle packaging

- **Languages**:
  - Python (API, resource processor)
  - TypeScript/JavaScript (UI)
  - Bash (deployment scripts)
  - HCL (Terraform)
  - YAML (CI/CD pipelines, Porter manifests)

- **Cloud Services**:
  - Azure services (App Service, Container Registry, Cosmos DB, etc.)
  - Microsoft Entra ID for authentication
  - Azure VMSS for resource processor

- **Development Tools**:
  - Docker for containerization
  - GitHub Actions for CI/CD
  - Make for build/deployment automation

## Repository Structure

```text
├── .github               - GitHub workflows, issue templates, and configuration
├── devops                - DevOps scripts and bootstrapping tools
├── docs                  - Documentation
├── e2e_tests             - pytest-based end-to-end tests
├── api_app               - API source code and docs
├── resource_processor    - VMSS Porter Runner
├── scripts               - Utility scripts
└── templates             - Resource templates
    ├── core/terraform    - Terraform definitions of Azure TRE core resources
    ├── shared_services   - Terraform definitions of shared services
    ├── workspace_services - Workspace services
    └── workspaces        - Workspace templates
```

## Coding Conventions

- **Python**:
  - Follow PEP 8 style guidelines
  - Use FastAPI for API endpoints
  - Use pytest for testing

- **Terraform**:
  - Use HCL format
  - Follow module structure conventions
  - Use variables.tf and outputs.tf for module interfaces
  - Include resource tagging for cost tracking

- **TypeScript/JavaScript**:
  - Follow standard ESLint configuration

- **YAML**:
  - Use consistent indentation (2 spaces)
  - Follow Porter best practices for bundle manifests

- **Git**:
  - Update CHANGELOG.md for all significant changes
  - Reference issue numbers in commit messages

## Environment Assumptions

- **Azure**: All resources are deployed in Azure
- **Microsoft Entra ID**: Used for authentication and authorization
- **Networking**: Core infrastructure uses hub-spoke networking model
- **Security**: Zero-trust security model with strict network boundaries
- **Deployment**: CI/CD through GitHub Actions

## Template Structure

Azure TRE uses Porter bundles to define workspaces, workspace services, and user resources. These bundles consist of:

### porter.yaml

This is the main Porter manifest file that defines:
- Credentials required for deployment
- Parameters and their defaults
- Actions (install, upgrade, uninstall)
- Mixins used (terraform, exec, etc.)
- Outputs from the deployment

Example structure:
```yaml
name: tre-service-example
version: 0.1.0
description: "An example TRE service"
registry: azuretre
...
```

### template_schema.json

JSON Schema file that defines the parameters that can be provided when deploying a resource. It follows standard JSON Schema format and is used by the API and UI to generate forms for resource creation.

Key sections include:
- Properties with types, descriptions, and defaults
- Required fields
- UI schema for customizing the display in the UI

### Terraform

Most bundles use Terraform to provision the actual resources in Azure. Common practices include:
- Breaking Terraform code into modules
- Using remote state for complex deployments
- Applying proper tagging for cost tracking
- Using variables.tf, main.tf, and outputs.tf
- Including lifecycle blocks to prevent resource recreation

## Changelog Updates

When creating a pull request, you must update the CHANGELOG.md file with your changes. Add your changes under one of these sections in the unreleased section at the top:

- ENHANCEMENTS
- BUG FIXES
- COMPONENTS (for version updates)

Format for changelog entries:
```markdown
* Brief description of change ([#1234](https://github.com/microsoft/AzureTRE/issues/1234))
```

Always include issue and/or PR references using the format `([#1234](https://github.com/microsoft/AzureTRE/issues/1234))`.

## Version Management

When editing components or bundles, you must increase their version numbers according to semantic versioning principles:

1. **MAJOR** version: Breaking changes, potential data loss, significant changes requiring review
2. **MINOR** version: New functionality with automatic upgrade capability
3. **PATCH** version: Backward-compatible bug or typo fixes

Version updates should be documented in:
1. The component's version file:
   - Porter bundles: in porter.yaml
   - API: in api_app/_version.py
   - Resource Processor: in resource_processor/_version.py
   - Airlock Processor: in airlock_processor/_version.py
   - UI: in ui/app/package.json

Example CHANGELOG entry for version updates:
```markdown
* Brief description of change ([#1234](https://github.com/microsoft/AzureTRE/issues/1234))
```

Always use semantic versioning (MAJOR.MINOR.PATCH) and follow versioning guidelines in the documentation.