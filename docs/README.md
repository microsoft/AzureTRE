# TRE documentation

The documentation is split into sections based on the level of knowledge needed.

- Business decision makers
- Azure administrators
- Workspace Template authors
- Developers

Common for all is the need to understand the TRE [concepts](concepts.md), [user roles](user-roles.md) and the first section with a high-level overview of the [solution architecture](architecture.md).

## Business decision makers

TODO

## Azure administrators

There are two ways to provision an instance of Azure TRE:

1. [Continuous integration & development (CI/CD) via Github Actions](cd-setup.md).
1. Follow the [scripted step-by-step guide](quickstart.md).

## Workspace Template authors

To create a new Workspace Template read the [Authoring Workspace Templates](authoring-workspace-templates.md), [Registering Workspace Templates](registering-workspace-templates.md) and if the Workspace Template needs to access public resource on the Internet, the [Authoring Firewall Rules](authoring-firewall-rules.md).

## Developers

To start extending the TRE fork the repository and setup a [CI/CD pipeline](cd-setup.md) which contains automated testing and continuous deployment into your environment.

Then follow the guide for developers to [setup a local development environment](developer-quickstart).

> Note: TRE is written in Python, Terraform, and with Bash scripts.
