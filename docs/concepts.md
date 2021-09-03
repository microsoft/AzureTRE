# Concepts

Trusted Research Environments (TRE) enforce a secure boundary around distinct workspaces to enable information governance controls to be enforced.

![Concepts](./assets/treconcepts.png)

A Trusted Research Environment (typically one per organization, or one per department in large organizations) consist of

- One Composition Service (API, deployment engine etc. used to manage and deploy workspaces, workspace services and user resources)
- One set of Shared Services used by all workspaces
- A number of workspaces, where each workspace is its own security boundary, and in turn contains Workspace Services and User Resources

Following are more detailed descriptions of the TRE concepts

- [Composition Service and API](#application-components-of-the-tre)
- [Services](#services)
- [Shared Services](#shared-services)
- [Workspace](#workspace)
- [Workspace Service](#workspace-service)
- [User Resource](#user-resource)
- [Templates](#templates)

## Application components of the TRE

A TRE consist of multiple processes orchestrating managing workspaces and services. These are components that enable researchers and TRE admins to provision and manage workspaces in a self-service manner. The components are of relevance for [Azure administrators](./user-roles.md#Azure-administrator), [TRE service integrator](./user-roles.md#TRE-service-integrator) and [TRE developers](./user-roles.md#Azure-TRE-developer).

### Composition Service

The Composition Service offers an abstraction over the lower-level Azure resources to allow for TRE users to provision resources in terms of workspaces and workspace services.

The Composition Service exposes resources – based on above concepts – as an HTTP API where users and applications can model the desired representation of the TRE, i.e., define which workspaces should contain which workspace services.

The Composition Service reconciles the desired state with the actual state by invoking Azure resource deployments.

## Services

A service provide one or more capabilities to you as a user of the TRE or to the TRE itself.  Depending on the type of the service it is scoped to the environment and shared across all workspaces (Shared Service) or scoped to a specific workspace (Workspace Service).

The types of services required for a research project varies greatly why extensibility is a key aspect of the Azure TRE solution. New services can be developed by you and your organization to fit your needs.

Some Workspace Services are accessible from outside the protected network, such as a Virtual Desktop. No data will be permitted to be transferred outside the protected network. Other services such as Azure Machine Learning might need access restricting to via a Virtual Desktop.

### Shared Services

Shared Services are services and resource shared by all workspaces.

- Firewall
- Package Mirror
- Git Mirror

## Workspace

A **Workspace** is a set of resources on a network with inbound traffic, restricted to authorised users, and outbound access restricted to defined network locations. The workspace is a security boundary and there should be zero transfer of data out from the workspace unless explicitly configured. Data transfer is not restricted within a workspace.

The workspace itself contains only the bare essentials to provide this functionality, such as firewalls, storage etc.

Workspaces can be enhanced with one or more building blocks called **workspace services** like Azure ML, Guacamole etc. to allow functionality such as development of machine learning models, data engineering, data analysis and software development.

Multiple workspaces can be created within a single Trusted Research Environment to create the required separation for your projects.

Each workspace has [workspace users](./user-roles.md): one workspace owner, and one or more workspace researchers that can access the data and workspace services in the workspace. The workspace owner is also considered a workspace researcher.

## Workspace Service

A workspace service is a service, created as a building block, with pre-configured set of resources that can be applied to a workspace.

Examples of Workspace Services are:

- Guacamole (Virtual Desktops)
- Azure Machine Learning

Unlike shared services, a workspace service is only accessible to the workspace users.

Some workspace services, such as Guacamole, allow users to add on user-specific resources (user resources)

All workspace services can be deployed to all workspaces.

## User Resource

A user resource is a resource that is only available to a particular researcher. For example a Guacamole VM.

User Resources can be deployed to workspaces with a compatible workspace service. E.g. Guacamole VMs can only be deployed to workspaces where the Guacamole workspace service is deployed.

## Templates

In order to deploy resources (workspaces, workspace services, user resources), the resources have to be defined in templates.

A template contains everything needed to create an instance of the resource. Ex. a base workspace template, or a Guacamole workspace service template.

The templates describe the porter bundles used, and the input parameters needed to deploy them.

To use a template, and deploy a resource, the template needs to be registered in the TRE. This is done using the TRE API.

> **Note:** Once a template is registered it can be used multiple times to deploy multiple workspaces, workspace services etc.

If you want to author your own workspace, workspace service, or user resource template, consult the [template authoring guide](./authoring-workspace-templates.md)
