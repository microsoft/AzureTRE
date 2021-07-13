# Azure TRE documentation

* Overview
  * [Concepts](./concepts.md)
  * [User roles](./user-roles.md)
  * [Architecture](./architecture.md)
  * [Logical data model](./logical-data-model.md)
* Getting started
  * [Dev environment](./dev-environment.md)
  * [Bootstrapping](./bootstrapping.md)
  * [Authentication & authorization](./auth.md)
  * The two ways of provisioning an instance of Azure TRE:
    1. [GitHub Actions workflows (CI/CD)](./workflows.md)
    1. [Manual deployment](./manual-deployment.md)
  * [Testing](./testing.md)
* Composition Service components
  * [Management API](../management_api_app/README.md)
  * [Resource Processor Function](../processor_function/README.md)
* Workspaces and workspace services
  * [Authoring workspace templates](./authoring-workspace-templates.md)
  * [Registering workspace templates](./registering-workspace-templates.md)
  * [Firewall rules](./firewall-rules.md)

## Repository structure

```text
├── .github
│   ├── ISSUE_TEMPLATE  - Templates for GitHub issues
│   ├── linters         - Linter definitions for workflows
│   └── workflows       - GitHub Actions workflows (CI/CD)
│
├── CNAB_container      - Container image used to run workspace deployments
│
├── devops
│   ├── scripts         - DevOps scripts
│   └── terraform       - Terraform specific DevOps files/scripts for bootstrapping
│
├── docs                - Documentation
│
├── e2e_tests           - pytest-based end-to-end tests
│
├── management_api_app  - Management API source code and docs
│
├── processor_function  - Resource Processor Function source code and docs
│
├── scripts             - Utility scripts
│
├── templates
│   ├── core/terraform  - Terraform definitions of Azure TRE core resources
│   └── services...     - Terraform definitions for default workspace resources
│
└── workspaces          - Workspace templates
```
