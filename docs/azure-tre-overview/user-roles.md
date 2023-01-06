# User roles

The Azure TRE solution has 8 different user roles defined. The roles are modeled around a set of tasks for each role. The roles are not mutually exclusive, and one person can have multiple roles assigned to be able to carry out a broader set of tasks.

Before you deploy a Trusted Research Environment based on the Azure TRE solution, you should consider your scenario and have an understanding of which of these roles that needs to be staffed.

## Role overview

While we have defined 8 different user roles for the Azure TRE solution, not all of them are required in all scenarios. Three of the roles support role-based access control (RBAC) within the TRE.  

| Role | Key task | TRE RBAC |
|------|----------|----------|
| Azure administrator | Deploy the TRE | |
| TRE administrator | Administer the TRE | ✔ |
| TRE workspace owner | Own a workspace | ✔ |
| Researcher | Perform research on the data | ✔ |
| Airlock Manager | Approves data import & export | ✔ |
| TRE service integrator | Integrate additional workspace services | |
| Azure TRE developer | Extend the TRE OSS solution | |
| Data engineer | Move data to and potentially from the TRE | |
| Information security officer | Validate and sign-off TRE deployment | |

!!! info
    More granular RBAC information is available [here](../tre-developers/api-permissions-map.md).

## Azure administrator

Provisions the Azure TRE solution in an Azure subscription and performs tasks that require knowledge of Azure operations and has access to the Azure subscription.

Example tasks:

- Provision Azure TRE solution instances.
- Second line support for TRE administrators, TRE workspace owners and Researchers when Azure TRE troubleshooting is required.
- Work with the data engineer to connect the Azure TRE with the data platform.
- Troubleshoot provisioning issues and failed deployments.
- Manage TRE administrator users.
- Manage data backups and restores.
- Update the Azure TRE instances.
- Configure log and metrics alerts.

Expected skills:

- Azure administration and operations.
- Infrastructure as Code (Terraform, ARM, Git)
- PowerShell, Bash

## TRE administrator

Day-to-day running and operations of the Azure TRE instance without touching Azure resources.

Example tasks:

- Manage workspace owner users.
- Provision workspaces.
- Manage shared services e.g., available packages in package mirror shared service.
- Monitor workspace usage and billing.
- Set and manage quotas.
- Create and manage workspaces

Expected skills:

- Limited or no Azure knowledge expected.

## TRE workspace owner

Owns a specific workspace and has additional privileges than the researcher within the workspace. Is most likely also a *Researcher*.

Example tasks:

- Manage Researcher users.
- Export data from workspace.
- Import data and make it available within the workspace.
- Enable services within the workspace.
- Monitor billing and usage of the workspace.
- Create and manage workspace services

Expected skills:

- Limited or no Azure knowledge expected.

## Researcher

Has access to one specific workspace and can use all the services provisioned within that workspace.

Example tasks:

- Import software packages needed to conduct research (PyPi, Conda, Apt).
- Perform research using the services in the workspace.
- Create and manage user resources

Expected skills:

- Python, R
- Git
- Linux

## Airlock Manager

Approves (and reviews in some instances) the data that is being imported to and exported from a TRE Workspace

Example tasks:

- Approve Airlock import requests
- Approve Airlock export requests
- Review the data being imported to and exported from a TRE Workspace

## TRE service integrator

Integrates workspace service types with an Azure TRE instance. This involves extending the Azure Infrastructure as Code templates to make a workspace service available within an Azure TRE instance.

Example tasks:

- Integrate a workspace service type with your Azure TRE instance.
- Implement Infrastructure as Code templates for new workspace service types.

Expected skills:

- Infrastructure as Code (Terraform, ARM, Git)
- Python, Bash
- Azure administration

## Azure TRE developer

Software developer who contributes to the development of the Azure TRE solution.

Example tasks:

- Modify the deployment service, API and other components of the Azure TRE solution.
- Contribute to the Azure TRE OSS solution.

Expected skills:

- Python, Bash
- Infrastructure as Code (Terraform, ARM, Git
- Azure administration

## Data engineer

Supporting role that is expected to build data movement pipelines between the data platform (not part of the TRE), and the TRE instance.

Example tasks:

- Transfer data from the data platform to the TRE and potentially back.
- Create data movement and transformation pipelines.

Expected skills:

- Python, Bash, Linux
- Azure Data Factory, Other ETL tools.

## Information Security Officer

Needs to understand the security posture of the TRE to ensure that the organization is compliant with the information governance framework and additional relevant regulations.

Example tasks:

- Use the Azure TRE documentation to understand the security posture of the TRE.
- Work with Azure administrator and TRE administrator to enforce the required security and privacy controls on the TRE.
- Commission penetration testing.
- Work with organization Information Governance committee to validate and sign-off Azure TRE deployment
