# OHDSI on Azure - Application Deployment

This guide will outline how to deploy OHDSI applications to your CDM on Azure.

To automate the application deployments, Azure DevOps pipelines are used. The pipelines will deploy the following applications:

- [WebAPI](https://github.com/OHDSI/WebAPI)
- [ATLAS](https://github.com/OHDSI/Atlas/)
- [ETL-Synthea](https://github.com/OHDSI/ETL-Synthea) (_optional_)
- [Achilles](https://github.com/OHDSI/Achilles)

## Prerequisites

- Azure resources spun up from Terraform (more information can be found in [Infrastructure Deployment](/infra/README.md))
- CDM Vocabulary uploaded to Storage Account
- Pipelines imported using YAML files

## Setup

The application deployment heavily relies on the use of docker images and Azure DevOps pipelines. There are two Docker images that are modified from OHDSI in order to be compatible with Azure: (1) [Broadsea WebTools Library](https://github.com/OHDSI/Broadsea-WebTools) (WebAPI + ATLAS) and (2) [Broadsea Methods Library](https://github.com/OHDSI/Broadsea-MethodsLibrary) (ETL-Synthea + Achilles).

You can also review the [setup Atlas / WebApi notes](/docs/setup/setup_atlas_webapi.md) and [setup Achilles / Synthea notes](/docs/setup/setup_achilles_synthea.md) for more details.

### 1. Broadsea Build and Push Pipeline (CI)

- This CI pipeline publishes the [WebAPI script](/sql/scripts/Web_Api_Refresh.sql) that will write sources to the `webapi` tables as a pipeline artifact.
- This CI pipeline also builds and pushes a custom OHDSI [Broadsea WebTools](/apps/broadsea-webtools/Dockerfile) Docker image to the environment container registry.

For more details, you can review the [broadsea build pipeline notes](/pipelines/README.md/#broadsea-build-pipeline)

### 2. Broadsea Release Pipeline (CD)

- The CD pipeline deploys the latest [Broadsea Webtools](/apps/broadsea-webtools/Dockerfile) Docker image to the App Service. This will download and install OHDSI WebAPI by creating the webapi schema in the CDM database.
- This pipeline serves to load synthetic test data to an OMOP CDM database.
- This pipeline leverages OHDSI's [ETL from Synthea](https://github.com/OHDSI/ETL-Synthea) project, which is an R library made to convert synthetic patient data from the [Synthea](https://github.com/synthetichealth/synthea) tool.
- This pipeline serves to run [Achilles](https://github.com/OHDSI/Achilles) characterization on a specific data set in the OMOP CDM, which should run each time new data is imported into the CDM.

For more details, you can review the [broadsea release pipeline notes](/pipelines/README.md/#broadsea-release-pipeline).
