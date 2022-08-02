<!-- markdownlint-disable MD041 -->
<!-- line format short be: change short description (#pr_numer) -->
## 0.5.0 (Unreleased)

**BREAKING CHANGES & MIGRATIONS**:

* Guacamole workspace service configures firewall requirements with deployment pipeline ([#2371](https://github.com/microsoft/AzureTRE/pull/2371)). **Migration** is manual - update the templateVersion of `tre-shared-service-firewall` in Cosmos to `0.4.0` in order to use this capability.
* Workspace now has an AirlockManager role that has the permissions to review airlock requests  ([#2349](https://github.com/microsoft/AzureTRE/pull/2349)).

FEATURES:

*

ENHANCEMENTS:

* Guacamole logs are sent to Application Insights ([#2376](https://github.com/microsoft/AzureTRE/pull/2376))
* `make tre-start / stop` run in parallel which saves ~5 minutes ([#2394](https://github.com/microsoft/AzureTRE/pull/2394))

BUG FIXES:

* Airlock processor creates SAS tokens with _user delegated key_ ([#2382](https://github.com/microsoft/AzureTRE/pull/2376))

## 0.4.0 (July 27, 2022)

FEATURES:

* Cost reporting APIs
* Airlock - data import/export
* UI
* Nexus v2 to support Docker repositories
* Auto create application registration when creating a base workspace
* Centrally manage the firewall share service state to enable other services to ask for rule changes

Many more enhancements are listed on the [release page](https://github.com/microsoft/AzureTRE/releases/tag/v0.4)

