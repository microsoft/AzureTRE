# Azure TRE Overview

## What is Azure TRE?

Across multiple industries, be it a pharmaceutical company interrogating clinical trial results, a public health provider analyzing electronic health records, or an engineering organization working on next-generation systems, there is a need to enable researchers and solution developers to collaborate on sensitive data.  

Trusted Research Environments (TREs) enable organisations to provide research and development (R&D) teams secure access to data alongside tooling to ensure productivity. Further information on TREs in general can be found in many places, one good resource specifically for healthcare is [HDR UK](https://www.hdruk.ac.uk/access-to-health-data/trusted-research-environments/).

Azure TRE is finding new applications and to date, has been used as the basis for exploring future secure collaboration environments in engineering. Workloads investigated include systems and software development. In truth, any workload in any industry could theoretically be supported with extensions to Azure TRE.

The Azure Trusted Research Environment project is an accelerator to assist Microsoft customers and partners who want to build out Trusted Research environments on Azure. This project enables authorized users to deploy and configure secure workspaces and R&D tooling without a dependency on IT teams.  

This project is typically implemented alongside a data platform that provides research ready datasets to TRE workspaces:

![Concepts](assets/TRE_Overview.png)

Azure TRE has also been proven to handle unstructured data scenarios. For example, collaborative Computer Aided Design (CAD), with Product Lifecycle Management integration.

TREs are not “one size fits all”, hence although the Azure TRE has a number of out of the box features, the project has been built be extensible, and hence tooling and data platform agnostic.

Core features include:

- Self-service for administrators – workspace creation and administration
- Self-service for R&D teams – R&D tooling creation and administration
- Package and repository mirroring
- Extensible architecture - build your own service templates as required
- Microsoft Entra ID integration
- Airlock
- Cost reporting
- Ready to workspace templates including:
  - Restricted with data exfiltration control
  - Unrestricted for open data
- Ready to go workspace service templates including:
  - Virtual Desktops: Windows, Linux
  - AzureML (Jupyter, R Studio, VS Code)
  - ML Flow, Gitea
