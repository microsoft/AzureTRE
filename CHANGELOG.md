<!-- markdownlint-disable MD041 -->
<!-- line format short be: change short description (#pr_numer) -->

## 0.5.0 (Unreleased)

**BREAKING CHANGES & MIGRATIONS**:

*

FEATURES:

*

ENHANCEMENTS:

* Adding Log Analytics & Antimalware VM extensions ([#2520](https://github.com/microsoft/AzureTRE/pull/2520))
* Block anonymous access to 2 storage accounts ([#2524](https://github.com/microsoft/AzureTRE/pull/2524))
* Gitea shared service support app-service standard SKUs ([#2523](https://github.com/microsoft/AzureTRE/pull/2523))
* Keyvault diagnostic settings in base workspace ([#2521](https://github.com/microsoft/AzureTRE/pull/2521))
* Airlock requests contain a field with information about the files that were submitted ([#2504](https://github.com/microsoft/AzureTRE/pull/2504))
* UI - Operations and notifications stability improvements ([[#2530](https://github.com/microsoft/AzureTRE/pull/2530))
* UI - Initial implemetation of Workspace Airlock Request View ([#2512](https://github.com/microsoft/AzureTRE/pull/2512))

BUG FIXES:

* API health check is also returned by accessing the root path at / ([#2469](https://github.com/microsoft/AzureTRE/pull/2469))
* Temporary disable AppInsight's private endpoint in base workspace ([#2543](https://github.com/microsoft/AzureTRE/pull/2543))
* Resource Processor execution optimization (`porter show`) for long-standing services ([#2542](https://github.com/microsoft/AzureTRE/pull/2542))

## 0.4.2 (August 23, 2022)

**BREAKING CHANGES & MIGRATIONS**:

* API identity is only assigned Virtual Machine Contributor on the workspace level ([#2398](https://github.com/microsoft/AzureTRE/pull/2398)). Review the PR for migration steps.


FEATURES:

* MySql workspace service ([#2476](https://github.com/microsoft/AzureTRE/pull/2476))

ENHANCEMENTS:

* 'CreationTime' field was added to Airlock requests ([#2432](https://github.com/microsoft/AzureTRE/pull/2432))
* Bundles mirror Terraform plugins when built ([#2446](https://github.com/microsoft/AzureTRE/pull/2446))
* 'Get all Airlock requests' endpoint supports filtering ([#2433](https://github.com/microsoft/AzureTRE/pull/2433))
* API uses user delagation key when generating SAS token for airlock requests ([#2460](https://github.com/microsoft/AzureTRE/pull/2460))
* Longer docker caching in Resource Processor ([#2486](https://github.com/microsoft/AzureTRE/pull/2486))
* Remove AppInsights Profiler support in base workspace bundle and deploy with native Terraform resources ([#2478](https://github.com/microsoft/AzureTRE/pull/2478))

BUG FIXES:

* Azure monitor resourced provided by Terraform and don't allow ingestion over internet ([#2375](https://github.com/microsoft/AzureTRE/pull/2375))
* Enable route table on the Airlock Processor subnet ([#2414](https://github.com/microsoft/AzureTRE/pull/2414))
* Support for _Standard_ app service plan SKUs ([#2415](https://github.com/microsoft/AzureTRE/pull/2415))
* Fix Azure ML Workspace deletion ([#2452](https://github.com/microsoft/AzureTRE/pull/2452))
* Get all pages in MS Graph queries ([#2492](https://github.com/microsoft/AzureTRE/pull/2492))

COMPONENTS:

| name | version |
| ----- | ----- |
| devops | 0.4.0 |
| core | 0.4.18 |
| tre-workspace-base | 0.3.19 |
| tre-workspace-base | 0.3.25 |
| tre-service-mlflow | 0.3.5 |
| tre-service-innereye | 0.3.3 |
| tre-workspace-service-gitea | 0.3.6 |
| tre-workspace-service-mysql | 0.1.0 |
| tre-service-guacamole-linuxvm | 0.4.11 |
| tre-service-guacamole-windowsvm | 0.4.4 |
| tre-service-guacamole | 0.4.3 |
| tre-user-resource-aml-compute-instance | 0.3.1 |
| tre-service-azureml | 0.4.3 |
| tre-shared-service-cyclecloud | 0.2.4 |
| tre-shared-service-gitea | 0.3.11 |
| tre-shared-service-airlock-notifier | 0.1.0 |
| tre-shared-service-certs | 0.1.2 |
| tre-shared-service-sonatype-nexus | 2.1.4 |
| tre-shared-service-firewall | 0.4.2 |
| tre-shared-service-nexus | 0.3.6 |

## 0.4.1 (August 03, 2022)

**BREAKING CHANGES & MIGRATIONS**:

* Guacamole workspace service configures firewall requirements with deployment pipeline ([#2371](https://github.com/microsoft/AzureTRE/pull/2371)). **Migration** is manual - update the templateVersion of `tre-shared-service-firewall` in Cosmos to `0.4.0` in order to use this capability.
* Workspace now has an AirlockManager role that has the permissions to review airlock requests ([#2349](https://github.com/microsoft/AzureTRE/pull/2349)).

FEATURES:

*

ENHANCEMENTS:

* Guacamole logs are sent to Application Insights ([#2376](https://github.com/microsoft/AzureTRE/pull/2376))
* `make tre-start/stop` run in parallel which saves ~5 minutes ([#2394](https://github.com/microsoft/AzureTRE/pull/2394))
* Airlock requests that fail move to status "Failed" ([#2268](https://github.com/microsoft/AzureTRE/pull/2395))

BUG FIXES:

* Airlock processor creates SAS tokens with _user delegated key_ ([#2382](https://github.com/microsoft/AzureTRE/pull/2382))
* Script updates to work with deployment repo structure ([#2385](https://github.com/microsoft/AzureTRE/pull/2385))

## 0.4.0 (July 27, 2022)

FEATURES:

* Cost reporting APIs
* Airlock - data import/export
* UI
* Nexus v2 to support Docker repositories
* Auto create application registration when creating a base workspace
* Centrally manage the firewall share service state to enable other services to ask for rule changes

Many more enhancements are listed on the [release page](https://github.com/microsoft/AzureTRE/releases/tag/v0.4)

