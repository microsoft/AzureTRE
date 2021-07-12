# Concepts

Trusted Research Environments enforce a secure boundary around distinct workspaces to enable information governance controls to be enforced. Each workspace is accessible by a set of authorized users, prevents the exfiltration of sensitive data, and has access to one or more datasets provided by the data platform.

One or more workspace services are deployed into a workspace to provide resources accessible by the [workspace users](./user-roles.md).

The workspaces and the services can be deployed and managed via the API of the Composition Service.

![Concepts](./assets/treconcepts.png)

## Workspace

A Workspace is a set of resources on a network with inbound traffic restricted to authorised users and outbound access restricted to defined network locations. The workspace is a security boundary in the fact there should be zero transfer of data outside of the workspace unless explicitly configured. Data transfer is not restricted within a workspace.

Workspaces can be configured with a variety of tools to enable tasks such as the development of machine learning models, data engineering, data analysis, and software development.

Multiple Workspaces can be created within a single Trusted Research Environment to create the required separation for your projects.

## Workspace Template

A Workspace Template is the model used to create Workspaces. It contains everything needed to create an instance of Workspace.
It is possible to create multiple instances of the same Workspace in one TRE.

## Service

A service provide one or more capabilities to you as a user of the TRE or to the TRE itself.  Depending on the type of the service it is scoped to the environment and shared across all workspaces (Shared Service) or scoped to a specific workspace (Workspace Service).

The types of services required for a research project varies greatly why extensibility is a key aspect of the Azure TRE solution. New services can be developed by you and your organization to fit your needs.

Some Workspace Services are accessible from outside the protected network, such as a Virtual Desktop. But no data will be permitted to be transferred outside the protected network. Other services such as Azure Machine Learning might need access restricting to via a Virtual Desktop.

Below are examples of services that are available in the Azure TRE solution.

### Shared Services

These are services and resource shared by all workspaces.

- Firewall
- Package Mirror
- Git Mirror

### Workspace Services

- Virtual Desktop
- Azure Machine Learning

## Application components of the TRE

TRE consist of multiple processes orchestrating managing Workspaces and services. These are components that enables Researchers and TRE Admins to provision and manage Workspaces in a self-service manor. These components are of relevance for [Azure Administrators](./user-roles.md#Azure-administrator), [TRE service integrator](./user-roles.md#TRE-service-integrator) and [TRE developers](./user-roles.md#TRE-developers).

### Composition Service

The Composition Service offers an abstraction over the lower-level Azure resources to allow for TRE users to provision resources in terms of workspaces and workspace services. The Composition Service exposes resources – based on above concepts – as an HTTP API where users and applications can model the desired representation of the TRE, i.e., define which workspaces should contain which workspace services.
The Composition Service reconciles the desired state with the actual state by invoking Azure resource deployments.
