# Azure TRE documentation

* Overview
  * [Concepts](./concepts.md)
  * [User roles](./user-roles.md)
  * [Architecture](./architecture.md)
  * [Networking](./networking.md)
  * [Logical data model](./logical-data-model.md)
* Getting started
  * [Dev environment](./dev-environment.md)
  * [Authentication & authorization](./auth.md)
  * The two ways of provisioning an instance of Azure TRE:
    1. [GitHub Actions workflows (CI/CD)](./workflows.md)
    1. [Quickstart](./deployment-quickstart.md)/[Manual deployment](./manual-deployment.md)
* Composition Service components
  * [API](../api_app/README.md)
  * [Resource Processor](../resource_processor/README.md)
  * [End-to-end tests](../e2e_tests/README.md)
* Workspaces and workspace services
  * [Authoring workspace templates](./authoring-workspace-templates.md)
  * [Registering workspace templates](./registering-workspace-templates.md)
  * [Firewall rules](./firewall-rules.md)

## Repository structure

```text
├── .github
│   ├── ISSUE_TEMPLATE     - Templates for GitHub issues
│   ├── linters            - Linter definitions for workflows
│   └── workflows          - GitHub Actions workflows (CI/CD)
│
├── devops
│   ├── scripts            - DevOps scripts
│   └── terraform          - Terraform specific DevOps files/scripts for bootstrapping
│
├── docs                   - Documentation
│
├── e2e_tests              - pytest-based end-to-end tests
│
├── api_app                - API source code and docs
│
├── resource_processor     - VMSS Porter Runner
│
├── scripts                - Utility scripts
│
└── templates
    ├── core/terraform     - Terraform definitions of Azure TRE core resources
    ├── shared_services    - Terraform definitions of shared services
    ├── workspace_services - Workspace services
    └── workspaces         - Workspace templates
```
