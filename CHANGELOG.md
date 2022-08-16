<!-- markdownlint-disable MD041 -->
<!-- line format short be: change short description (#pr_numer) -->
## 0.5.0 (Unreleased)

**BREAKING CHANGES & MIGRATIONS**:

* API identity is only assigned Virtual Machine Contributor on the workspace level ([#2398](https://github.com/microsoft/AzureTRE/pull/2398)). Review the PR for migration steps.


FEATURES:

*

ENHANCEMENTS:

* 'CreationTime' field was added to Airlock requests ([#2432](https://github.com/microsoft/AzureTRE/issues/2432))
* Bundles mirror Terraform plugins when built ([#2446](https://github.com/microsoft/AzureTRE/pull/2446))
* 'Get all Airlock requests' endpoint supports filtering ([#2433](https://github.com/microsoft/AzureTRE/pull/2433)).
* API uses user delagation key when generating SAS token for airlock requests. ([#2390](https://github.com/microsoft/AzureTRE/issues/2390))

BUG FIXES:

* Azure monitor resourced provided by Terraform and don't allow ingestion over internet ([#2375](https://github.com/microsoft/AzureTRE/pull/2375))
* Enable route table on the Airlock Processor subnet ([#2414](https://github.com/microsoft/AzureTRE/pull/2414))
* Support for _Standard_ app service plan SKUs ([#2415](https://github.com/microsoft/AzureTRE/pull/2415))
* Fix Azure ML Workspace deletion ([#2452](https://github.com/microsoft/AzureTRE/pull/2452))

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

