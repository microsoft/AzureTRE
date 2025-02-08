# Azure Trusted Research Environment

**Azure TRE documentation site**: <https://microsoft.github.io/AzureTRE/>

## Background
<img align="right" src="./docs/assets/azure-tre-logo.svg" width="33%" />

Across multiple industries, be it a pharmaceutical company interrogating clinical trial results, a public health provider analyzing electronic health records, or an engineering organization working on next-generation systems, there is a need to enable researchers and solution developers to collaborate on sensitive data.

Trusted Research Environments (TREs) enable organisations to provide research and development (R&D) teams secure access to data alongside tooling to ensure productivity while keeping security controls in place.

Further information on TREs in general can be found in many places, one good resource specifically for healthcare is [HDR UK's website](https://www.hdruk.ac.uk/access-to-health-data/trusted-research-environments/).

Azure TRE is finding new applications and to date, has been used as the basis for exploring future secure collaboration environments in engineering. Workloads investigated include systems and software development. In truth, any workload in any industry could theoretically be supported with extensions to Azure TRE.

The Azure Trusted Research Environment project is an accelerator to assist Microsoft customers and partners who want to build out Trusted Research environments on Azure. This project enables authorized users to deploy and configure secure workspaces and researcher tooling without a dependency on IT teams.

This project is typically implemented alongside a data platform that provides research ready datasets to TRE workspaces. Azure TRE has also been proven to handle unstructured data scenarios. For example, collaborative Computer Aided Design (CAD), with Product Lifecycle Management integration.

TREs are not “one size fits all”, hence although the Azure TRE has a number of out of the box features, the project has been built be extensible, and hence tooling and data platform agnostic.

Core features include:
- Self-service workspace management for TRE administrators
- Self-service provisioning of R&D tooling for R&D teams
- Package and repository mirroring - PyPi, R-CRAN, Apt and more.
- Extensible architecture - build your own service templates as required
- Microsoft Entra ID integration
- Airlock - import and export
- Cost reporting
- Ready to workspace templates including:  
  - Restricted with data exfiltration control
  - Unrestricted for open data
- Ready to go workspace service templates including:
  - Virtual Desktops: Windows, Linux
  - AzureML (Jupyter, R Studio, VS Code)
  - ML Flow
  - Gitea

## Project Status and Support

***This project's code base is still under development and breaking changes will happen. Whilst the maintainers will do our best to minimise disruption to existing deployments, this may not always be possible. Stable releases will be published when the project is more mature.***

The aim is to bring together learnings from past customer engagements where TREs have been built into a single reference solution. This is a solution accelerator aiming to be a great starting point for a customized TRE solution. You're encouraged to download and customize the solution to meet your requirements

This project does not have a dedicated team of maintainers but relies on you and the community to maintain and enhance the solution. Microsoft will on project-to-project basis continue to extend the solution in collaboration with customers and partners. No guarantees can be offered as to response times on issues, feature requests, or to the long term road map for the project.

It is important before deployment of the solution that the [Support Policy](SUPPORT.md) is read and understood.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [https://cla.opensource.microsoft.com](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

Note: maintainers should refer to the [maintainers guide](maintainers.md)

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.


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
