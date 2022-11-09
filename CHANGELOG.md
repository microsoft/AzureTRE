<!-- markdownlint-disable MD041 -->
<!-- line format short be: change short description (#pr_numer) -->
## 0.6.1 (Unreleased)

**BREAKING CHANGES & MIGRATIONS**:
* The airlock request object has changed. Make sure you have ran the db migration step after deploying the new API image and UI (which runs automatically in `make all`/`make tre-deploy` but can be manually invoked with `make db-migrate`) so that existing requests in your DB are migrated to the new model.
* Also the model for creating new airlock requests with the API has changed slightly; this is updated in the UI and CLI but if you have written custom tools ensure you are POSTing to `/requests` with the following model:
```json
{
    "type": "'import' or 'export'",
    "title": "a request title",
    "businessJustification": "some business justification"
}
```
* Fields in AirlockNotification event have changed without backward compatibility. If Airlock Notifier shared service is deployed, it needs to be re-deployed. Any other consumers of AirlockNotification event need to be updated. For more details, see [#2798](https://github.com/microsoft/AzureTRE/pull/2798)

FEATURES:
* Display workspace and shared services total costs for admin role in UI [#2738](https://github.com/microsoft/AzureTRE/pull/2772)
* Automatically validate all resources have tre_id tag via TFLint [#2774](https://github.com/microsoft/AzureTRE/pull/2774)
* Add metadata endpoint and simplify `tre` CLI login (also adds API version to UI) (#2794)
* Updated resource card in UI with visual improvements, disabled state badge and resource ID in info popout [#2846](https://github.com/microsoft/AzureTRE/pull/2846)
* Add health information for backend services to UI info popout in footer [#2846](https://github.com/microsoft/AzureTRE/pull/2846)

ENHANCEMENTS:
* Renamed several airlock fields to make them more descriptive and added a createdBy field. Included migration for backwards compatibility ([#2779](https://github.com/microsoft/AzureTRE/pull/2779))
* Show error message when Review VMs are not configured in the current workspace
* CLI: Add missing endpoints and minor bug fixes (#2784)
* Airlock Notifier: Provide a link to request in the UI in the email ([#2754](https://github.com/microsoft/AzureTRE/pull/2754))
* Add additional fields for Airlock Notification event ([#2798](https://github.com/microsoft/AzureTRE/pull/2798))
* Fail firewall database migration if there's no firewall deployed ([#2792](https://github.com/microsoft/AzureTRE/pull/2792))
* Added optional parameter to allow a client to retrieve a template by name and version ([#2802](https://github.com/microsoft/AzureTRE/pull/2802))
* Added support for `allOf` usage in Resource Templates - both across the API and the UI. This allows a template author to specify certain fields as being conditionally present / conditionally required, and means we can tidy up some of the resource creation forms substantially ([#2795](https://github.com/microsoft/AzureTRE/pull/2795)).
* As part of the above change, the `auto_create` string passed to the `client_id` field in each Workspace template has now moved to an `auth_type` enum field, where the user can select the authentication type from a dropdown.
* Adds extra dns zones and links into core network ([#2828](https://github.com/microsoft/AzureTRE/pull/2828)).
* Add UI version to its footer card ([#2849](https://github.com/microsoft/AzureTRE/pull/2849)).

BUG FIXES:
* Show the correct createdBy value for airlock requests in UI and in API queries ([#2779](https://github.com/microsoft/AzureTRE/pull/2779))
* Fix deployment of Airlock Notifier ([#2745](https://github.com/microsoft/AzureTRE/pull/2745))
* Fix Nexus bootstrapping firewall race condition ([#2811](https://github.com/microsoft/AzureTRE/pull/2811))
* Handle unsupported azure subscriptions in cost reporting ([#2823](https://github.com/microsoft/AzureTRE/pull/2823))

COMPONENTS:

## 0.6.0 (October 24, 2022)

FEATURES:
* Added filtering and sorting to Airlock UI ([#2511](https://github.com/microsoft/AzureTRE/pull/2730))
* Added title field to Airlock requests ([#2503](https://github.com/microsoft/AzureTRE/pull/2731))
* New Create Review VM functionality for Airlock Reviews ([#2738](https://github.com/microsoft/AzureTRE/pull/2759) & [#2737](https://github.com/microsoft/AzureTRE/pull/2740))



ENHANCEMENTS:
* Add cran support to nexus, open port 80 for the workspace nsg and update the firewall config to allow let's encrypt CRLs ([#2694](https://github.com/microsoft/AzureTRE/pull/2694))
* Upgrade Github Actions versions ([#2731](https://github.com/microsoft/AzureTRE/pull/2744))
* Install TRE CLI inside the devcontainer image (rather than via a post-create step) ([#2757](https://github.com/microsoft/AzureTRE/pull/2757))
* Upgrade Terraform to 1.3.2 ([#2758](https://github.com/microsoft/AzureTRE/pull/2758))
* `tre` CLI: added `raw` output option, improved `airlock-requests` handling, more consistent exit codes on error, added examples to CLI README.md

BUG FIXES:
* Pin Porter's plugin/mixin versions used ([#2762](https://github.com/microsoft/AzureTRE/pull/2762))
* Fix issues with AML workspace service deployment ([#2768](https://github.com/microsoft/AzureTRE/pull/2768))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.4.2 |
| core | 0.4.37 |
| tre-workspace-base | 0.4.2 |
| tre-workspace-unrestricted | 0.2.0 |
| tre-workspace-airlock-import-review | 0.4.0 |
| tre-service-mlflow | 0.4.0 |
| tre-service-innereye | 0.4.0 |
| tre-workspace-service-gitea | 0.5.0 |
| tre-workspace-service-mysql | 0.2.0 |
| tre-service-guacamole-linuxvm | 0.5.2 |
| tre-service-guacamole-export-reviewvm | 0.0.6 |
| tre-service-guacamole-windowsvm | 0.5.2 |
| tre-service-guacamole-import-reviewvm | 0.1.3 |
| tre-service-guacamole | 0.5.0 |
| tre-user-resource-aml-compute-instance | 0.4.1 |
| tre-service-azureml | 0.5.6 |
| tre-shared-service-cyclecloud | 0.3.0 |
| tre-shared-service-gitea | 0.4.0 |
| tre-shared-service-airlock-notifier | 0.2.2 |
| tre-shared-service-admin-vm | 0.2.0 |
| tre-shared-service-certs | 0.2.0 |
| tre-shared-service-sonatype-nexus | 2.2.2 |
| tre-shared-service-firewall | 0.6.1 |

## 0.5.1 (October 12, 2022)

BUG FIXES:

* Fix shared service 409 installation issue when in status other than deployed ([#2725](https://github.com/microsoft/AzureTRE/pull/2725))

COMPONENTS:

| name | version |
| ----- | ----- |
| devops | 0.4.2 |
| core | 0.4.36 |
| tre-workspace-base | 0.4.0 |
| tre-workspace-unrestricted | 0.2.0 |
| tre-workspace-airlock-import-review | 0.4.0 |
| tre-service-mlflow | 0.4.0 |
| tre-service-innereye | 0.4.0 |
| tre-workspace-service-gitea | 0.5.0 |
| tre-workspace-service-mysql | 0.2.0 |
| tre-service-guacamole-linuxvm | 0.5.1 |
| tre-service-guacamole-export-reviewvm | 0.0.4 |
| tre-service-guacamole-windowsvm | 0.5.1 |
| tre-service-guacamole-import-reviewvm | 0.1.1 |
| tre-service-guacamole | 0.5.0 |
| tre-user-resource-aml-compute-instance | 0.4.1 |
| tre-service-azureml | 0.5.1 |
| tre-shared-service-cyclecloud | 0.3.0 |
| tre-shared-service-gitea | 0.4.0 |
| tre-shared-service-airlock-notifier | 0.2.0 |
| tre-shared-service-admin-vm | 0.2.0 |
| tre-shared-service-certs | 0.2.0 |
| tre-shared-service-sonatype-nexus | 2.2.0 |
| tre-shared-service-firewall | 0.6.1 |


## 0.5.0 (October 10, 2022)

**BREAKING CHANGES & MIGRATIONS**:

* Github Actions deployments use a single ACR instead of two. Github secrets might need updating, see PR for details. ([#2654](https://github.com/microsoft/AzureTRE/pull/2654))
* Align Github Action secret names. Existing Github environments must be updated, see PR for details. ([#2655](https://github.com/microsoft/AzureTRE/pull/2655))
* Add workspace creator as an owner of the workspace enterprise application ([#2627](https://github.com/microsoft/AzureTRE/pull/2627)). **Migration** if the `AUTO_WORKSPACE_APP_REGISTRATION` is set, the `Directory.Read.All` MS Graph API permission permission needs granting to the Application Registration identified by `APPLICATION_ADMIN_CLIENT_ID`.
* Add support for setting AppService plan SKU in GitHub Actions. Previous environment variable names of `API_APP_SERVICE_PLAN_SKU_SIZE` and `APP_SERVICE_PLAN_SKU` have been renamed to `CORE_APP_SERVICE_PLAN_SKU` and `WORKSPACE_APP_SERVICE_PLAN_SKU` ([#2684](https://github.com/microsoft/AzureTRE/pull/2684))
* Reworked how status update messages are handled by the API, to enforce ordering and run the queue subscription in a dedicated thread. Since sessions are now enabled for the status update queue, a `tre-deploy` is required, which will re-create the queue. ([#2700](https://github.com/microsoft/AzureTRE/pull/2700))
* Guacamole user-resource templates have been updated. VM SKU and image details are now specified in `porter.yaml`. See `README.md` in the guacamole `user-resources` folder for details.
* `deploy_shared_services.sh` now uses the `tre` CLI. Ensure that your CI/CD environment installs the CLI (`(cd cli && make install-cli)`)
* UI: Moved from React Context API to React-Redux (with Redux Toolkit) to manage the global operations (notifications) state

FEATURES:

* Add Import Review Workspace ([#2498](https://github.com/microsoft/AzureTRE/issues/2498))
* Restrict resource templates to specific roles ([#2600](https://github.com/microsoft/AzureTRE/issues/2600))
* Import review user resource template ([#2601](https://github.com/microsoft/AzureTRE/issues/2601))
* Export review user resource template ([#2602](https://github.com/microsoft/AzureTRE/issues/2602))
* Airlock Manager can use user resources ([#2499](https://github.com/microsoft/AzureTRE/issues/2499))
* Users only see templates they are authorized to use ([#2640](https://github.com/microsoft/AzureTRE/issues/2640))
* Guacamole user-resource templates now have support for custom VM images from image galleries ([#2634](https://github.com/microsoft/AzureTRE/pull/2634))
* Add initial `tre` CLI ([2537](https://github.com/microsoft/AzureTRE/pull/2537))

ENHANCEMENTS:

* Cancelling an Airlock request triggers deletion of the request container and files ([#2584](https://github.com/microsoft/AzureTRE/pull/2584))
* Airlock requests with status "blocked_by_scan" have the reason for being blocked by the malware scanner in the status_message field ([#2666](https://github.com/microsoft/AzureTRE/pull/2666))
* Move admin-vm from core to a shared service ([#2624](https://github.com/microsoft/AzureTRE/pull/2624))
* Remove obsolete docker environment variables ([#2675](https://github.com/microsoft/AzureTRE/pull/2675))
* Using Porter's Terrform mixin 1.0.0-rc.1 where mirror in done internally ([#2677](https://github.com/microsoft/AzureTRE/pull/2677))
* Airlock function internal storage is accessed with private endpoints ([#2679](https://github.com/microsoft/AzureTRE/pull/2679))

BUG FIXES:

* Resource processor error on deploying user-resource: TypeError: 'NoneType' object is not iterable ([#2569](https://github.com/microsoft/AzureTRE/issues/2569))
* Update Porter and Terraform mixin versions ([#2639](https://github.com/microsoft/AzureTRE/issues/2639))
* Airlock Manager should have permissions to get SAS token ([#2502](https://github.com/microsoft/AzureTRE/issues/2502))
* Terraform unmarshal errors in `migrate.sh` ([#2673](https://github.com/microsoft/AzureTRE/issues/2673))

COMPONENTS:

| name | version |
| ----- | ----- |
| devops | 0.4.2 |
| core | 0.4.36 |
| porter-hello | 0.1.0 |
| tre-workspace-base-sl-test | 0.3.19 |
| tre-workspace-base | 0.4.0 |
| tre-workspace-unrestricted | 0.2.0 |
| tre-workspace-airlock-import-review | 0.4.0 |
| tre-service-mlflow | 0.4.0 |
| tre-service-innereye | 0.4.0 |
| tre-workspace-service-gitea | 0.5.0 |
| tre-workspace-service-mysql | 0.2.0 |
| tre-service-guacamole-linuxvm | 0.5.1 |
| tre-service-guacamole-export-reviewvm | 0.0.4 |
| tre-service-guacamole-windowsvm | 0.5.1 |
| tre-service-guacamole-import-reviewvm | 0.1.1 |
| tre-service-guacamole | 0.5.0 |
| tre-user-resource-aml-compute-instance | 0.4.1 |
| tre-service-azureml | 0.5.1 |
| tre-shared-service-cyclecloud | 0.3.0 |
| tre-shared-service-gitea | 0.4.0 |
| tre-shared-service-airlock-notifier | 0.2.0 |
| tre-shared-service-admin-vm | 0.2.0 |
| tre-shared-service-certs | 0.2.0 |
| tre-shared-service-sonatype-nexus | 2.2.0 |
| tre-shared-service-firewall | 0.6.1 |



## 0.4.3 (September 12, 2022)

**BREAKING CHANGES & MIGRATIONS**:

* Remove support for Nexus V1 ([#2580](https://github.com/microsoft/AzureTRE/pull/2580)). Please migrate to the newer version as described [here](https://microsoft.github.io/AzureTRE/tre-admins/setup-instructions/configuring-shared-services/).

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
* Add ability to automatically create Azure AD groups for each application role. Requires API version 0.4.30 or later ([#2532](https://github.com/microsoft/AzureTRE/pull/2532))
* Add `is_expsed_externally` option to Azure ML Workspace Service ([#2548](https://github.com/microsoft/AzureTRE/pull2548))
* Azure ML workspace service assigns Azure ML Data Scientist role to Workspace Researchers ([#2539](https://github.com/microsoft/AzureTRE/pull/2539))
* UI is deployed by default ([#2554](https://github.com/microsoft/AzureTRE/pull/2554))
* Remove manual/makefile option to install Gitea/Nexus ([#2573](https://github.com/microsoft/AzureTRE/pull/2573))
* Exact Terraform provider versions in bundles ([#2579](https://github.com/microsoft/AzureTRE/pull/2579))
* Stabilize E2E tests by issuing the access token prior using it, hence, reducing the change of expired token ([#2572](https://github.com/microsoft/AzureTRE/pull/2572))

BUG FIXES:

* API health check is also returned by accessing the root path at / ([#2469](https://github.com/microsoft/AzureTRE/pull/2469))
* Temporary disable AppInsight's private endpoint in base workspace ([#2543](https://github.com/microsoft/AzureTRE/pull/2543))
* Resource Processor execution optimization (`porter show`) for long-standing services ([#2542](https://github.com/microsoft/AzureTRE/pull/2542))
* Move AML Compute deployment to use AzApi Terraform Provider {[#2555]((https://github.com/microsoft/AzureTRE/pull/2555))
* Invalid token exceptions in the API app are catched, throwing 401 instead of 500 Internal server error ([#2572](https://github.com/microsoft/AzureTRE/pull/2572))

COMPONENTS:

| name | version |
| ----- | ----- |
| devops | 0.4.0 |
| core | 0.4.23 |
| tre-workspace-base | 0.3.28 |
| tre-workspace-unrestricted | 0.1.9 |
| tre-service-mlflow | 0.3.7 |
| tre-service-innereye | 0.3.5 |
| tre-workspace-service-gitea | 0.3.8 |
| tre-workspace-service-mysql | 0.1.2 |
| tre-service-guacamole-linuxvm | 0.4.14 |
| tre-service-guacamole-windowsvm | 0.4.8 |
| tre-service-guacamole | 0.4.5 |
| tre-user-resource-aml-compute-instance | 0.3.2 |
| tre-service-azureml | 0.4.8 |
| tre-shared-service-cyclecloud | 0.2.6 |
| tre-shared-service-gitea | 0.3.14 |
| tre-shared-service-airlock-notifier | 0.1.2 |
| tre-shared-service-certs | 0.1.3 |
| tre-shared-service-sonatype-nexus | 2.1.6 |
| tre-shared-service-firewall | 0.4.3 |

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

