# Concepts

Trusted Research Environments enforce a secure boundary around distinct workspaces to enable information governance controls to be enforced. Each workspace is accessible by a set of authorized users, prevents the exfiltration of sensitive data, and has access to one or more datasets provided by the data platform.

One or more workspace services are deployed into a workspace to provide resources accessible by the [workspace users](./user-roles.md).

The workspaces and the services can be deployed and managed via the API of the Composition Service.

![Concepts](./assets/treconcepts.png)

## Workspace

A workspace is a set of resources on a network with inbound traffic restricted to authorised users and outbound access restricted to defined network locations. The workspace is a security boundary in the fact there should be zero transfer of data outside of the workspace unless explicitly configured. Data transfer is not restricted within a workspace.

Workspaces can be configured with a variety of tools to enable tasks such as the development of machine learning models, data engineering, data analysis, and software development.

Multiple workspaces can be created within a single Trusted Research Environment to create the required separation for your projects.

## Service

A service provide one or more capabilities to you as a user of the TRE or to the TRE itself.  Depending on the type of the service it is scoped to the environment and shared across all workspaces (Shared service) or scoped to a specific workspace (Workspace service).

The types of services required for a research project varies greatly why extensibility is a key aspect of the Azure TRE solution. New services can be developed by you and your organization to fit your needs.

Some workspace services are accessible from outside the protected network, such as a Virtual Desktop. But no data will be permitted to be transferred outside the protected network. Other services such as Azure Machine Learning might need access restricting to via a Virtual Desktop.

Below are examples of services that are available in the Azure TRE solution.

### Shared services

These are services and resource shared by all workspaces.

- Firewall
- Application Package Mirror
- Git Mirror

### Workspace services

- Virtual Desktop
- Azure Machine Learning

## Composition Service

The composition service offers an abstraction over the lower-level Azure resources to allow for TRE users to provision resources in terms of workspaces and workspace services.
The composition service exposes resources – based on above concepts – as an HTTP API where users and applications can model the desired representation of the TRE, i.e., define which workspaces should contain which workspace services.
The composition service reconciles the desired state with the actual state by invoking Azure resource deployments.
