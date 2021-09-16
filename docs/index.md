# Azure TRE documentation

* Overview
  * [Concepts](azure-tre-overview/concepts.md)
  * [User roles](azure-tre-overview/user-roles.md)
  * [Architecture](azure-tre-overview/architecture.md)
  * [Networking](azure-tre-overview/networking.md)
  * [Logical data model](./logical-data-model.md)
* Getting started
  * [Dev environment](tre-developers/dev-environment.md)
  * [Authentication & authorization](tre-admins/deploying-the-tre/auth.md)
  * The two ways of provisioning an instance of Azure TRE:
    1. [GitHub Actions workflows (CI/CD)](tre-admins/deploying-the-tre/workflows.md)
    1. [Quickstart](./deployment-quickstart.md)/[Manual deployment](tre-admins/deploying-the-tre/manual-deployment.md)
* Composition Service components
  * [API](azure-tre-overview/composition-service/api.md)
  * [Resource Processor](azure-tre-overview/composition-service/resource-processor.md)
  * [End-to-end tests](tre-developers/end-to-end-tests.md)
* Workspaces and workspace services
  * [Authoring workspace templates](tre-workspace-authors/authoring-workspace-templates.md)
  * [Registering workspace templates](tre-workspace-authors/registering-workspace-templates.md)
  * [Firewall rules](tre-workspace-authors/firewall-rules.md)

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
