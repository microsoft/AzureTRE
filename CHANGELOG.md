<!-- markdownlint-disable MD041 -->
## 0.20.0 (Unreleased)

**BREAKING CHANGES & MIGRATIONS**:

FEATURES:

ENHANCEMENTS:

BUG FIXES:

COMPONENTS:

## 0.19.1

**BREAKING CHANGES & MIGRATIONS**:
* Workspace creation blocked due to Azure API depreciation ([#4095](https://github.com/microsoft/AzureTRE/issues/4095))

ENHANCEMENTS:
* Update Unrestricted and Airlock Import Review workspaces to be built off the Base workspace 0.19.0 ([#4087](https://github.com/microsoft/AzureTRE/pull/4087))
* Update Release Docs (part of [#2727](https://github.com/microsoft/AzureTRE/issues/2727))
* Add info regarding workspace limit into docs ([#3920](https://github.com/microsoft/AzureTRE/issues/3920))

BUG FIXES:
* Workspace creation blocked due to Azure API depreciation ([#4095](https://github.com/microsoft/AzureTRE/issues/4095))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.2 |
| core | 0.10.8 |
| ui | 0.5.28 |
| tre-service-guacamole-linuxvm | 1.0.3 |
| tre-service-guacamole-import-reviewvm | 0.2.9 |
| tre-service-guacamole-export-reviewvm | 0.1.9 |
| tre-service-guacamole-windowsvm | 1.0.1 |
| tre-service-guacamole | 0.10.9 |
| tre-service-databricks | 1.0.4 |
| tre-service-mlflow | 0.7.9 |
| tre-service-innereye | 0.6.5 |
| tre-workspace-service-ohdsi | 0.2.5 |
| tre-workspace-service-gitea | 1.0.5 |
| tre-workspace-service-mysql | 1.0.4 |
| tre-workspace-service-azuresql | 1.0.10 |
| tre-user-resource-aml-compute-instance | 0.5.7 |
| tre-service-azureml | 0.8.11 |
| tre-workspace-service-health | 0.2.6 |
| tre-workspace-service-openai | 1.0.1 |
| tre-workspace-airlock-import-review | 0.13.1 |
| tre-workspace-unrestricted | 0.12.1 |
| tre-workspace-base | 1.5.7 |
| tre-shared-service-cyclecloud | 0.6.3 |
| tre-shared-service-databricks-private-auth | 0.1.6 |
| tre-shared-service-sonatype-nexus | 3.0.1 |
| tre-shared-service-admin-vm | 0.4.4 |
| tre-shared-service-firewall | 1.2.1 |
| tre-shared-service-gitea | 1.0.3 |
| tre-shared-service-certs | 0.5.2 |
| tre-shared-service-airlock-notifier | 1.0.2 |

## 0.19.0

FEATURES:
* Azure SQL Workspace Service ([#3969](https://github.com/microsoft/AzureTRE/issues/3969))
* OpenAI Workspace Service ([#3810](https://github.com/microsoft/AzureTRE/issues/3810))

ENHANCEMENTS:
* Add Case Study Docs ([#1366](https://github.com/microsoft/AzureTRE/issues/1366))
* Ability to host TRE on a custom domain ([#4014](https://github.com/microsoft/AzureTRE/pull/4014))
* Remove AppServiceFileAuditLogs diagnostic setting ([#4033](https://github.com/microsoft/AzureTRE/issues/4033))
* Update to the Airlock Notifier Shared Service ([#3909](https://github.com/microsoft/AzureTRE/issues/3909))

BUG FIXES:
* Removed 429 Error (Costs API) form presenting in UI ([#3929](https://github.com/microsoft/AzureTRE/issues/3929))
* Fix numbering issue within `bug_report.md` template ([#4028](https://github.com/microsoft/AzureTRE/pull/4028))
* Disable public network access to the API App Service ([#3986](https://github.com/microsoft/AzureTRE/issues/3986))
* Fix Guacamole shared drive always enabled ([#3885](https://github.com/microsoft/AzureTRE/issues/3885))
* Add Dependabot Security updates for July
* Update Docs to format emojis properly ([#4027](https://github.com/microsoft/AzureTRE/issues/4027))
* Update API and Resource Processor opentelemetry versions ([#4052](https://github.com/microsoft/AzureTRE/issues/4052))
* Fix broken links in new Case Study Docs
* Update Linux VM to stop screensaver locking out the user ([#4065](https://github.com/microsoft/AzureTRE/issues/4065))
* Update .NET version on Linux VMs ([#4067](https://github.com/microsoft/AzureTRE/issues/4067))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.10.6 |
| ui | 0.5.28 |
| tre-service-guacamole-linuxvm | 1.0.2 |
| tre-service-guacamole-import-reviewvm | 0.2.8 |
| tre-service-guacamole-export-reviewvm | 0.1.8 |
| tre-service-guacamole-windowsvm | 1.0.0 |
| tre-service-guacamole | 0.10.8 |
| tre-service-databricks | 1.0.3 |
| tre-service-mlflow | 0.7.8 |
| tre-service-innereye | 0.6.4 |
| tre-workspace-service-ohdsi | 0.2.4 |
| tre-workspace-service-gitea | 1.0.3 |
| tre-workspace-service-mysql | 1.0.2 |
| tre-workspace-service-azuresql | 1.0.9 |
| tre-user-resource-aml-compute-instance | 0.5.7 |
| tre-service-azureml | 0.8.10 |
| tre-workspace-service-health | 0.2.5 |
| tre-workspace-airlock-import-review | 0.12.16 |
| tre-workspace-unrestricted | 0.11.4 |
| tre-workspace-base | 1.5.4 |
| tre-shared-service-cyclecloud | 0.5.5 |
| tre-shared-service-databricks-private-auth | 0.1.5 |
| tre-shared-service-sonatype-nexus | 3.0.0 |
| tre-shared-service-admin-vm | 0.4.3 |
| tre-shared-service-firewall | 1.2.0 |
| tre-shared-service-gitea | 1.0.2 |
| tre-shared-service-certs | 0.5.1 |
| tre-shared-service-airlock-notifier | 1.0.1 |

## 0.18.0

**BREAKING CHANGES & MIGRATIONS**:
* Update Core Terraform Provider versions ([#3919](https://github.com/microsoft/AzureTRE/issues/3919))
* Introduction of config value `enable_airlock_email_check`, which defaults to `false`, this is a change in behaviour. If you require email addresses for users before an airlock request is created, set to `true`. ([#3904](https://github.com/microsoft/AzureTRE/issues/3904))

FEATURES:

ENHANCEMENTS:
* Additional DataBrick IPs added ([#3901](https://github.com/microsoft/AzureTRE/issues/3901))
* Add KeyVault Purge Protection Variable ([#3922](https://github.com/microsoft/AzureTRE/issues/3922))
* Update Guacamole Windows 11 VM Image to 2Win11-23h2-pro ([#3995](https://github.com/microsoft/AzureTRE/issues/3995))
* Make check for email addresses prior to an airlock request being created optional. ([#3904](https://github.com/microsoft/AzureTRE/issues/3904))
* Add Firewall SKU variable ([#3961](https://github.com/microsoft/AzureTRE/issues/3961))

BUG FIXES:
* Update Guacamole Linux VM Images to Ubuntu 22.04 LTS. Part of ([#3523](https://github.com/microsoft/AzureTRE/issues/3523))
* Update Nexus Shared Service with new proxies. Part of ([#3523](https://github.com/microsoft/AzureTRE/issues/3523))
* Update to Resource Processor Image, now using Ubuntu 22.04 (jammy). Part of ([#3523](https://github.com/microsoft/AzureTRE/issues/3523))
* Remove TLS1.0/1.1 support from Application Gateway ([#3914](https://github.com/microsoft/AzureTRE/issues/3914))
* GitHub Actions version updates. ([#3847](https://github.com/microsoft/AzureTRE/issues/3847))
* Add workaround to avoid name clashes for storage accounts([#3863](https://github.com/microsoft/AzureTRE/pull/3858))
* Resource processor fails to deploy first workspace on fresh TRE deployment ([#3950](https://github.com/microsoft/AzureTRE/issues/3950))
* Dependency and Vulnerability updates
* Fix Weak hashes ([#3931](https://github.com/microsoft/AzureTRE/issues/3931))
* Add lifecycle rule to MySQL resources to stop them recreating on `update` ([#3993](https://github.com/microsoft/AzureTRE/issues/3993))
* Fixes broken links on 'Using the Azure TRE -> Custom Templates' page of documentation ([[#4003](https://github.com/microsoft/AzureTRE/issues/4003)])
* Fix 'Renew Lets Encrypt Certificates' GitHub Action ([#3978](https://github.com/microsoft/AzureTRE/issues/3978))
* Add lifecycle rule to the Gitea Shared Service template for the MySQL resource to stop it recreating on `update` ([#4006](https://github.com/microsoft/AzureTRE/issues/4006))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.10.1 |
| ui | 0.5.24 |
| tre-service-guacamole-linuxvm | 1.0.0 |
| tre-service-guacamole-import-reviewvm | 0.2.8 |
| tre-service-guacamole-export-reviewvm | 0.1.8 |
| tre-service-guacamole-windowsvm | 1.0.0 |
| tre-service-guacamole | 0.10.7 |
| tre-service-databricks | 1.0.3 |
| tre-service-mlflow | 0.7.7 |
| tre-service-innereye | 0.6.4 |
| tre-workspace-service-ohdsi | 0.2.4 |
| tre-workspace-service-gitea | 1.0.2 |
| tre-workspace-service-mysql | 1.0.2 |
| tre-user-resource-aml-compute-instance | 0.5.7 |
| tre-service-azureml | 0.8.10 |
| tre-workspace-service-health | 0.2.5 |
| tre-workspace-airlock-import-review | 0.12.16 |
| tre-workspace-unrestricted | 0.11.4 |
| tre-workspace-base | 1.5.3 |
| tre-shared-service-cyclecloud | 0.5.5 |
| tre-shared-service-databricks-private-auth | 0.1.5 |
| tre-shared-service-sonatype-nexus | 3.0.0 |
| tre-shared-service-admin-vm | 0.4.3 |
| tre-shared-service-firewall | 1.2.0 |
| tre-shared-service-gitea | 1.0.1 |
| tre-shared-service-certs | 0.5.1 |
| tre-shared-service-airlock-notifier | 0.9.0 |

## 0.17.0

**BREAKING CHANGES & MIGRATIONS**:
* Update terraform MySQL resources to MySQL Flexible resources to fix depricating recources. ([#3892](https://github.com/microsoft/AzureTRE/pull/3892)) - Migration to new version of Gitea and MySQL, needs to be carried out manually, details to be included in a later release.

ENHANCEMENTS:
* Switch from OpenCensus to OpenTelemetry for logging ([#3762](https://github.com/microsoft/AzureTRE/pull/3762))
* Extend PowerShell auto start script to start core VMs ([#3811](https://github.com/microsoft/AzureTRE/issues/3811))
* Use managed identity for API connection to CosmosDB ([#345](https://github.com/microsoft/AzureTRE/issues/345))
* Switch to Structured Firewall Logs ([#3816](https://github.com/microsoft/AzureTRE/pull/3816))
* Support for building core and workspace service bundles on arm64 platforms ([#3823](https://github.com/microsoft/AzureTRE/issues/3823))

BUG FIXES:
* Fix issue with workspace menu not working correctly([#3819](https://github.com/microsoft/AzureTRE/issues/3819))
* Fix issue with connect button showing when no uri([#3820](https://github.com/microsoft/AzureTRE/issues/3820))
* Fix user resource upgrade validation: use the parent_service_template_name instead of the parent_resource_id. ([#3824](https://github.com/microsoft/AzureTRE/issues/3824))
* Airlock: Creating an import/export request causes a routing error ([#3830](https://github.com/microsoft/AzureTRE/issues/3830))
* Fix registration of templates with no 'authorizedRoles' or 'required' defined ([#3849](https://github.com/microsoft/AzureTRE/pull/3849))
* Update terraform for services bus to move network rules into namespace resource to avoid depreciation warning, and update setup_local_debugging.sh to use network_rule_sets ([#3858](https://github.com/microsoft/AzureTRE/pull/3858))
* Update terraform MySQL resources to MySQL Flexible resources to fix depricating recources. ([#3892](https://github.com/microsoft/AzureTRE/pull/3892))
* Fix issue with firewall failing to deploy on a new TRE deploy ([#3775](https://github.com/microsoft/AzureTRE/issues/3775))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.9.6 |
| ui | 0.5.21 |
| tre-service-guacamole-linuxvm | 0.6.9 |
| tre-service-guacamole-import-reviewvm | 0.2.8 |
| tre-service-guacamole-export-reviewvm | 0.1.8 |
| tre-service-guacamole-windowsvm | 0.7.9 |
| tre-service-guacamole | 0.10.6 |
| tre-service-databricks | 1.0.3 |
| tre-service-mlflow | 0.7.7 |
| tre-service-innereye | 0.6.4 |
| tre-workspace-service-ohdsi | 0.2.4 |
| tre-workspace-service-gitea | 1.0.1 |
| tre-workspace-service-mysql | 1.0.1 |
| tre-user-resource-aml-compute-instance | 0.5.7 |
| tre-service-azureml | 0.8.10 |
| tre-workspace-service-health | 0.2.5 |
| tre-workspace-airlock-import-review | 0.12.16 |
| tre-workspace-unrestricted | 0.11.4 |
| tre-workspace-base | 1.5.3 |
| tre-shared-service-cyclecloud | 0.5.5 |
| tre-shared-service-databricks-private-auth | 0.1.5 |
| tre-shared-service-sonatype-nexus | 2.8.13 |
| tre-shared-service-admin-vm | 0.4.3 |
| tre-shared-service-firewall | 1.1.7 |
| tre-shared-service-gitea | 1.0.1 |
| tre-shared-service-certs | 0.5.1 |
| tre-shared-service-airlock-notifier | 0.9.0 |

## 0.16.0 (December 1, 2023)

**BREAKING CHANGES & MIGRATIONS**:
To resolve the Airlock import issue described in ([#3767](https://github.com/microsoft/AzureTRE/pull/3767)), the new airlock import review template will need to be registered using `make workspace_bundle BUNDLE=airlock-import-review`. Any existing airlock import review workspaces will need to be upgraded.

Once you have upgraded the import review workspaces, delete the private endpoint, named `pe-stg-import-inprogress-blob-*` in the core resource group, and then run `make deploy-core` to reinstate the private endpoint and DNS records.

ENHANCEMENTS:
* Security updates aligning to Dependabot, MS Defender for Cloud and Synk ([#3796](https://github.com/microsoft/AzureTRE/issues/3796))

BUG FIXES:
* Fix issue where updates fail as read only is not configured consistently on schema fields ([#3691](https://github.com/microsoft/AzureTRE/issues/3691))
* When getting available address spaces allow those allocated to deleted workspaces to be reassigned ([#3691](https://github.com/microsoft/AzureTRE/issues/3691))
* Update Python packages, and fix breaking changes ([#3764](https://github.com/microsoft/AzureTRE/issues/3764))
* Enabling support for more than 20 users/groups in Workspace API ([#3759](https://github.com/microsoft/AzureTRE/pull/3759  ))
* Airlock Import Review workspace uses dedicated DNS zone to prevent conflict with core ([#3767](https://github.com/microsoft/AzureTRE/pull/3767))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.9.0 |
| ui | 0.5.17 |
| tre-workspace-base | 1.5.3 |
| tre-workspace-unrestricted | 0.11.4 |
| tre-workspace-airlock-import-review | 0.12.16 |
| tre-service-mlflow | 0.7.7 |
| tre-workspace-service-health | 0.2.5 |
| tre-service-databricks | 1.0.3 |
| tre-service-innereye | 0.6.4 |
| tre-workspace-service-gitea | 0.8.7 |
| tre-workspace-service-mysql | 0.4.5 |
| tre-workspace-service-ohdsi | 0.2.4 |
| tre-service-guacamole-linuxvm | 0.6.9 |
| tre-service-guacamole-export-reviewvm | 0.1.8 |
| tre-service-guacamole-windowsvm | 0.7.9 |
| tre-service-guacamole-import-reviewvm | 0.2.8 |
| tre-service-guacamole | 0.10.6 |
| tre-user-resource-aml-compute-instance | 0.5.7 |
| tre-service-azureml | 0.8.10 |
| tre-shared-service-cyclecloud | 0.5.5 |
| tre-shared-service-databricks-private-auth | 0.1.5 |
| tre-shared-service-gitea | 0.6.10 |
| tre-shared-service-airlock-notifier | 0.9.0 |
| tre-shared-service-admin-vm | 0.4.3 |
| tre-shared-service-certs | 0.5.1 |
| tre-shared-service-sonatype-nexus | 2.8.13 |
| tre-shared-service-firewall | 1.1.5 |


## 0.15.2 (October 24, 2023)

BUG FIXES:
* Remove .sh extension from nexus renewal script so CRON job executes ([#3742](https://github.com/microsoft/AzureTRE/issues/3742))
* Upgrade porter version to v1.0.15 and on error getting porter outputs return dict ([#3744](https://github.com/microsoft/AzureTRE/issues/3744))
* Fix notifications displaying workspace name rather than actual resource ([#3746](https://github.com/microsoft/AzureTRE/issues/3746))
* Fix SecuredByRole fails if app roles are not loaded  ([#3752](https://github.com/microsoft/AzureTRE/issues/3752))
* Fix workspace not loading fails if operation or history roles are not loaded  ([#3755](https://github.com/microsoft/AzureTRE/issues/3755))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.8.9 |
| ui | 0.5.15 |
| tre-workspace-base | 1.5.0 |
| tre-workspace-unrestricted | 0.11.1 |
| tre-workspace-airlock-import-review | 0.12.7 |
| tre-service-mlflow | 0.7.7 |
| tre-workspace-service-health | 0.2.5 |
| tre-service-databricks | 1.0.3 |
| tre-service-innereye | 0.6.4 |
| tre-workspace-service-gitea | 0.8.7 |
| tre-workspace-service-mysql | 0.4.5 |
| tre-workspace-service-ohdsi | 0.2.4 |
| tre-service-guacamole-linuxvm | 0.6.9 |
| tre-service-guacamole-export-reviewvm | 0.1.8 |
| tre-service-guacamole-windowsvm | 0.7.9 |
| tre-service-guacamole-import-reviewvm | 0.2.8 |
| tre-service-guacamole | 0.10.5 |
| tre-user-resource-aml-compute-instance | 0.5.7 |
| tre-service-azureml | 0.8.10 |
| tre-shared-service-cyclecloud | 0.5.5 |
| tre-shared-service-databricks-private-auth | 0.1.5 |
| tre-shared-service-gitea | 0.6.10 |
| tre-shared-service-airlock-notifier | 0.9.0 |
| tre-shared-service-admin-vm | 0.4.3 |
| tre-shared-service-certs | 0.5.1 |
| tre-shared-service-sonatype-nexus | 2.8.13 |
| tre-shared-service-firewall | 1.1.5 |


## 0.15.1 (October 12, 2023)

BUG FIXES:
* SecuredByRole failing if roles are null ([#3740](https://github.com/microsoft/AzureTRE/issues/3740  ))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.8.9 |
| ui | 0.5.11 |
| tre-workspace-base | 1.5.0 |
| tre-workspace-unrestricted | 0.11.1 |
| tre-workspace-airlock-import-review | 0.12.7 |
| tre-service-mlflow | 0.7.7 |
| tre-workspace-service-health | 0.2.5 |
| tre-service-databricks | 1.0.3 |
| tre-service-innereye | 0.6.4 |
| tre-workspace-service-gitea | 0.8.7 |
| tre-workspace-service-mysql | 0.4.5 |
| tre-workspace-service-ohdsi | 0.2.4 |
| tre-service-guacamole-linuxvm | 0.6.9 |
| tre-service-guacamole-export-reviewvm | 0.1.8 |
| tre-service-guacamole-windowsvm | 0.7.9 |
| tre-service-guacamole-import-reviewvm | 0.2.8 |
| tre-service-guacamole | 0.10.5 |
| tre-user-resource-aml-compute-instance | 0.5.7 |
| tre-service-azureml | 0.8.10 |
| tre-shared-service-cyclecloud | 0.5.5 |
| tre-shared-service-databricks-private-auth | 0.1.5 |
| tre-shared-service-gitea | 0.6.10 |
| tre-shared-service-airlock-notifier | 0.9.0 |
| tre-shared-service-admin-vm | 0.4.3 |
| tre-shared-service-certs | 0.5.1 |
| tre-shared-service-sonatype-nexus | 2.8.12 |
| tre-shared-service-firewall | 1.1.5 |

## 0.15.0 (October 10, 2023)

FEATURES:

ENHANCEMENTS:
* Reduce logging noise ([#2135](https://github.com/microsoft/AzureTRE/issues/2135))
* Update workspace template to use Terraform's AzureRM 3.73 ([#3715](https://github.com/microsoft/AzureTRE/pull/3715))
* Enable cost tags for workspace services and user resources ([#2932](https://github.com/microsoft/AzureTRE/issues/2932))

BUG FIXES:
* Upgrade unresticted and airlock base template versions due to diagnostic settings retention period being depreciated ([#3704](https://github.com/microsoft/AzureTRE/pull/3704))
* Enable TRE Admins to view workspace details when don't have a workspace role ([#2363](https://github.com/microsoft/AzureTRE/issues/2363))
* Fix shared services list return restricted resource for admins causing issues with updates ([#3716](https://github.com/microsoft/AzureTRE/issues/3716))
* Fix grey box appearing on resource card when costs are not available. ([#3254](https://github.com/microsoft/AzureTRE/issues/3254))
* Fix notification panel not passing the workspace scope id to the API hence UI not updating ([#3353](https://github.com/microsoft/AzureTRE/issues/3353))
* Fix issue with cost tags not displaying correctly for some user roles ([#3721](https://github.com/microsoft/AzureTRE/issues/3721))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.8.9 |
| tre-workspace-base | 1.5.0 |
| tre-workspace-unrestricted | 0.11.1 |
| tre-workspace-airlock-import-review | 0.12.7 |
| tre-service-mlflow | 0.7.7 |
| tre-workspace-service-health | 0.2.5 |
| tre-service-databricks | 1.0.3 |
| tre-service-innereye | 0.6.4 |
| tre-workspace-service-gitea | 0.8.7 |
| tre-workspace-service-mysql | 0.4.5 |
| tre-workspace-service-ohdsi | 0.2.4 |
| tre-service-guacamole-linuxvm | 0.6.9 |
| tre-service-guacamole-export-reviewvm | 0.1.8 |
| tre-service-guacamole-windowsvm | 0.7.9 |
| tre-service-guacamole-import-reviewvm | 0.2.8 |
| tre-service-guacamole | 0.10.5 |
| tre-user-resource-aml-compute-instance | 0.5.7 |
| tre-service-azureml | 0.8.10 |
| tre-shared-service-cyclecloud | 0.5.5 |
| tre-shared-service-databricks-private-auth | 0.1.5 |
| tre-shared-service-gitea | 0.6.10 |
| tre-shared-service-airlock-notifier | 0.9.0 |
| tre-shared-service-admin-vm | 0.4.3 |
| tre-shared-service-certs | 0.5.1 |
| tre-shared-service-sonatype-nexus | 2.8.12 |
| tre-shared-service-firewall | 1.1.5 |

## 0.14.1 (September 1, 2023)

BUG FIXES:
* Fix firewall config related to Nexus so that `pypi.org` is added to the allow-list  ([#3694](https://github.com/microsoft/AzureTRE/issues/3694))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.8.6 |
| tre-workspace-base | 1.4.7 |
| tre-workspace-unrestricted | 0.10.4 |
| tre-workspace-airlock-import-review | 0.11.6 |
| tre-service-mlflow | 0.7.5 |
| tre-workspace-service-health | 0.2.4 |
| tre-service-databricks | 1.0.3 |
| tre-service-innereye | 0.6.4 |
| tre-workspace-service-gitea | 0.8.5 |
| tre-workspace-service-mysql | 0.4.4 |
| tre-workspace-service-ohdsi | 0.2.3 |
| tre-service-guacamole-linuxvm | 0.6.8 |
| tre-service-guacamole-export-reviewvm | 0.1.7 |
| tre-service-guacamole-windowsvm | 0.7.8 |
| tre-service-guacamole-import-reviewvm | 0.2.7 |
| tre-service-guacamole | 0.10.4 |
| tre-user-resource-aml-compute-instance | 0.5.7 |
| tre-service-azureml | 0.8.10 |
| tre-shared-service-cyclecloud | 0.5.4 |
| tre-shared-service-databricks-private-auth | 0.1.5 |
| tre-shared-service-gitea | 0.6.5 |
| tre-shared-service-airlock-notifier | 0.9.0 |
| tre-shared-service-admin-vm | 0.4.3 |
| tre-shared-service-certs | 0.5.1 |
| tre-shared-service-sonatype-nexus | 2.8.11 |
| tre-shared-service-firewall | 1.1.4 |

## 0.14.0 (August 25, 2023)

ENHANCEMENTS:
* Change Guacamole username claim to `preferred_username`, so email not required ([#3539](https://github.com/microsoft/AzureTRE/issues/3539))
* Upgrade Ubuntu version for Sonatype Nexus VM to 22.04 LTS ([#3523](https://github.com/microsoft/AzureTRE/issues/3523))

BUG FIXES:
* Add temporary workaround for when id with last 4 chars exists ([#3667](https://github.com/microsoft/AzureTRE/pull/3667))
* Apply missing lifecycle blocks. ([#3670](https://github.com/microsoft/AzureTRE/issues/3670))
* Outputs of type boolean are stored as strings ([#3655](https://github.com/microsoft/AzureTRE/pulls/3655))
* Add dependency on firewall deployment to rule collection ([#3672](https://github.com/microsoft/AzureTRE/pulls/3672))
* Check docker return code in set docker sock permissions file ([#3674](https://github.com/microsoft/AzureTRE/pulls/3674))
* Increase reliability of Nexus deployment ([[#3642](https://github.com/microsoft/AzureTRE/issues/3642))
* Add firewall rule to allow airlock to download functions runtime ([#3682](https://github.com/microsoft/AzureTRE/pull/3682))
* Update dev container so doesn't try to create new group with clashing ID, only updates user ID ([#3682](https://github.com/microsoft/AzureTRE/pull/3682))
* Remove diagnostic settings retention period as has been depreciated ([#3682](https://github.com/microsoft/AzureTRE/pull/3682))
* Added missing region entries in `databricks-udr.json` ([[#3688](https://github.com/microsoft/AzureTRE/pull/3688))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.8.6 |
| tre-workspace-base | 1.4.7 |
| tre-workspace-unrestricted | 0.10.4 |
| tre-workspace-airlock-import-review | 0.11.6 |
| tre-service-mlflow | 0.7.5 |
| tre-workspace-service-health | 0.2.4 |
| tre-service-databricks | 1.0.3 |
| tre-service-innereye | 0.6.4 |
| tre-workspace-service-gitea | 0.8.5 |
| tre-workspace-service-mysql | 0.4.4 |
| tre-workspace-service-ohdsi | 0.2.3 |
| tre-service-guacamole-linuxvm | 0.6.8 |
| tre-service-guacamole-export-reviewvm | 0.1.7 |
| tre-service-guacamole-windowsvm | 0.7.8 |
| tre-service-guacamole-import-reviewvm | 0.2.7 |
| tre-service-guacamole | 0.10.4 |
| tre-user-resource-aml-compute-instance | 0.5.7 |
| tre-service-azureml | 0.8.10 |
| tre-shared-service-cyclecloud | 0.5.4 |
| tre-shared-service-databricks-private-auth | 0.1.5 |
| tre-shared-service-gitea | 0.6.5 |
| tre-shared-service-airlock-notifier | 0.9.0 |
| tre-shared-service-admin-vm | 0.4.3 |
| tre-shared-service-certs | 0.5.1 |
| tre-shared-service-sonatype-nexus | 2.8.10 |
| tre-shared-service-firewall | 1.1.4 |


## 0.13.0 (August 9, 2023)

BUG FIXES:
* Custom actions fail on resources with a pipeline ([#3646](https://github.com/microsoft/AzureTRE/issues/3646))
* Fix ability to debug resource processor locally ([#3426](https://github.com/microsoft/AzureTRE/issues/4426))
* Upgrade airlock and unrestricted workspaces to base workspace version 0.12.0 ([#3659](https://github.com/microsoft/AzureTRE/pull/3659))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.8.3 |
| tre-workspace-base | 1.4.4 |
| tre-workspace-unrestricted | 0.10.2 |
| tre-workspace-airlock-import-review | 0.11.2 |
| tre-service-mlflow | 0.7.2 |
| tre-workspace-service-health | 0.2.1 |
| tre-service-databricks | 1.0.0 |
| tre-service-innereye | 0.6.1 |
| tre-workspace-service-gitea | 0.8.2 |
| tre-workspace-service-mysql | 0.4.1 |
| tre-workspace-service-ohdsi | 0.2.0 |
| tre-service-guacamole-linuxvm | 0.6.5 |
| tre-service-guacamole-export-reviewvm | 0.1.4 |
| tre-service-guacamole-windowsvm | 0.7.5 |
| tre-service-guacamole-import-reviewvm | 0.2.4 |
| tre-service-guacamole | 0.9.4 |
| tre-user-resource-aml-compute-instance | 0.5.4 |
| tre-service-azureml | 0.8.7 |
| tre-shared-service-cyclecloud | 0.5.1 |
| tre-shared-service-databricks-private-auth | 0.1.2 |
| tre-shared-service-gitea | 0.6.2 |
| tre-shared-service-airlock-notifier | 0.9.0 |
| tre-shared-service-admin-vm | 0.4.0 |
| tre-shared-service-certs | 0.5.1 |
| tre-shared-service-sonatype-nexus | 2.5.3 |
| tre-shared-service-firewall | 1.1.1 |


## 0.12.0 (July 27, 2023)

FEATURES:
* OHDSI workspace service ([#3562](https://github.com/microsoft/AzureTRE/issues/3562))

ENHANCEMENTS:
* Workspace networking peering sync is handled natively by Terraform ([#3534](https://github.com/microsoft/AzureTRE/issues/3534))
* Use SMTP built in connector vs API connector in Airlock Notifier ([#3572](https://github.com/microsoft/AzureTRE/issues/3572))
* Update Guacamole dependencies ([#3602](https://github.com/microsoft/AzureTRE/issues/3602))

BUG FIXES:
* Nexus might fail to deploy due to wrong identity used in key-vault extension ([#3492](https://github.com/microsoft/AzureTRE/issues/3492))
* Airlock notifier needs SCM basic-auth enabled to install ([#3509](https://github.com/microsoft/AzureTRE/issues/3509))
* Databricks fails to deploy in East US ([#3515](https://github.com/microsoft/AzureTRE/issues/3515))
* `load_env.sh` is able to use an equal `=` sign in values ([#3535](https://github.com/microsoft/AzureTRE/issues/3535))
* Make AML route names unique ([#3546](https://github.com/microsoft/AzureTRE/issues/3546))
* Azure ML connection URI is an object, not string ([#3486](https://github.com/microsoft/AzureTRE/issues/3486))
* Update key in Linux VM deploy script ([#3434](https://github.com/microsoft/AzureTRE/issues/3434))
* Add missing `azure_environment` porter parameters ([#3549](https://github.com/microsoft/AzureTRE/issues/3549))
* Fix airlock_notifier not getting the right smtp password ([#3561](https://github.com/microsoft/AzureTRE/issues/3561))
* Fix issue when deleting failed resources gives no steps ([#3567](https://github.com/microsoft/AzureTRE/issues/3567))
* Fix airlock_notifier not getting the right smtp password ([#3565](https://github.com/microsoft/AzureTRE/issues/3565))
* Fix issues with networking dependencies and AMPLS deployment ([#3433](https://github.com/microsoft/AzureTRE/issues/3433))
* Update CLI install method to fix dependency issue ([#3601](https://github.com/microsoft/AzureTRE/issues/3601))
* Update Databricks UDRs for west europe and switch to DFS private endpoint. ([[#3582](https://github.com/microsoft/AzureTRE/issues/3582))


COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.8.2 |
| tre-workspace-base | 1.4.4 |
| tre-workspace-airlock-import-review | 0.10.1 |
| tre-workspace-unrestricted | 0.9.0 |
| tre-workspace-service-gitea | 0.8.1 |
| tre-service-guacamole | 0.9.3 |
| tre-service-guacamole-windowsvm | 0.7.5 |
| tre-service-guacamole-import-reviewvm | 0.2.4 |
| tre-service-guacamole-linuxvm | 0.6.5 |
| tre-service-guacamole-export-reviewvm | 0.1.4 |
| tre-workspace-service-health | 0.2.1 |
| tre-workspace-service-ohdsi | 0.2.0 |
| tre-service-azureml | 0.8.7 |
| tre-user-resource-aml-compute-instance | 0.5.4 |
| tre-service-mlflow | 0.7.1 |
| tre-service-databricks | 1.0.0 |
| tre-workspace-service-mysql | 0.4.1 |
| tre-service-innereye | 0.6.1 |
| tre-shared-service-cyclecloud | 0.5.1 |
| tre-shared-service-airlock-notifier | 0.9.0 |
| tre-shared-service-gitea | 0.6.1 |
| tre-shared-service-certs | 0.5.0 |
| tre-shared-service-databricks-private-auth | 0.1.1 |
| tre-shared-service-admin-vm | 0.4.0 |
| tre-shared-service-sonatype-nexus | 2.5.2 |
| tre-shared-service-firewall | 1.1.1 |

## 0.11.0 (April 24, 2023)

ENHANCEMENTS:
* Update Guacamole to version 1.5.1 ([#3443](https://github.com/microsoft/AzureTRE/issues/3443))
* Popup to copy internally accessible URLs ([#3420](https://github.com/microsoft/AzureTRE/issues/3420))

BUG FIXES:
* AML workspace service fails to install and puts firewall into failed state ([#3448](https://github.com/microsoft/AzureTRE/issues/3448))
* Nexus fails to install due to `az login` and firewall rules ([#3453](https://github.com/microsoft/AzureTRE/issues/3453))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.8.1 |
| tre-workspace-base | 1.2.3 |
| tre-workspace-unrestricted | 0.9.0 |
| tre-workspace-airlock-import-review | 0.10.1 |
| tre-service-mlflow | 0.7.1 |
| tre-workspace-service-health | 0.2.1 |
| tre-service-databricks | 0.2.1 |
| tre-service-innereye | 0.6.1 |
| tre-workspace-service-gitea | 0.8.1 |
| tre-workspace-service-mysql | 0.4.1 |
| tre-service-guacamole-linuxvm | 0.6.5 |
| tre-service-guacamole-export-reviewvm | 0.1.4 |
| tre-service-guacamole-windowsvm | 0.7.4 |
| tre-service-guacamole-import-reviewvm | 0.2.4 |
| tre-service-guacamole | 0.9.0 |
| tre-user-resource-aml-compute-instance | 0.5.4 |
| tre-service-azureml | 0.8.2 |
| tre-shared-service-cyclecloud | 0.5.1 |
| tre-shared-service-databricks-private-auth | 0.1.1 |
| tre-shared-service-gitea | 0.6.1 |
| tre-shared-service-airlock-notifier | 0.5.0 |
| tre-shared-service-admin-vm | 0.4.0 |
| tre-shared-service-certs | 0.5.0 |
| tre-shared-service-sonatype-nexus | 2.5.0 |
| tre-shared-service-firewall | 1.1.1 |

## 0.10.0 (April 16, 2023)

**BREAKING CHANGES & MIGRATIONS**:
* A migration for OperationSteps in Operation objects was added ([#3358](https://github.com/microsoft/AzureTRE/pull/3358))
* Some Github _secrets_ have moved to be _environment variables_ - `LOCATION` and a few optional others will need to be redefined as listed [here](https://microsoft.github.io/AzureTRE/latest/tre-admins/setup-instructions/cicd-pre-deployment-steps/#configure-core-variables) ([#3084](https://github.com/microsoft/AzureTRE/pull/3084))

FEATURES:
* (UI) Added upgrade button to resources that have pending template upgrades ([#3387](https://github.com/microsoft/AzureTRE/pull/3387))
* Enable deployment to Azure US Government Cloud ([#3128](https://github.com/microsoft/AzureTRE/issues/3128))

ENHANCEMENTS:
* Added 'availableUpgrades' field to Resources in GET/GET all Resources endpoints. The field indicates whether there are template versions that a resource can be upgraded to [#3234](https://github.com/microsoft/AzureTRE/pull/3234)
* Update Porter (1.0.11), Docker (23.0.3), Terraform (1.4.5) ([#3430](https://github.com/microsoft/AzureTRE/issues/3430))
* Build, publish and register Databricks bundles in workflow ([#3447](https://github.com/microsoft/AzureTRE/issues/3447))


BUG FIXES:
* Fix ENABLE_SWAGGER configuration being ignored in CI ([#3355](https://github.com/microsoft/AzureTRE/pull/3355))
* Set yq output format when reading a json file ([#3441](https://github.com/microsoft/AzureTRE/pull/3441))
* Set `{}` as the workflow default for `RP_BUNDLE_VALUES` parameter ([#3444](https://github.com/microsoft/AzureTRE/pull/3444))

COMPONENTS:

| name | version |
| ----- | ----- |
| devops | 0.5.1 |
| core | 0.8.1 |
| tre-shared-service-admin-vm | 0.4.0 |
| tre-shared-service-airlock-notifier | 0.5.0 |
| tre-shared-service-certs | 0.5.0 |
| tre-shared-service-cyclecloud | 0.5.1 |
| tre-shared-service-databricks-private-auth | 0.1.1 |
| tre-shared-service-firewall | 1.1.0 |
| tre-shared-service-gitea | 0.6.1 |
| tre-shared-service-sonatype-nexus | 2.4.0 |
| tre-service-azureml | 0.8.1 |
| tre-user-resource-aml-compute-instance | 0.5.4 |
| tre-service-databricks | 0.2.1 |
| tre-workspace-service-gitea | 0.8.1 |
| tre-service-guacamole | 0.8.4 |
| tre-service-guacamole-export-reviewvm | 0.1.4 |
| tre-service-guacamole-import-reviewvm | 0.2.4 |
| tre-service-guacamole-linuxvm | 0.6.5 |
| tre-service-guacamole-windowsvm | 0.7.4 |
| tre-workspace-service-health | 0.2.1 |
| tre-service-innereye | 0.6.1 |
| tre-service-mlflow | 0.7.1 |
| tre-workspace-service-mysql | 0.4.1 |
| tre-workspace-airlock-import-review | 0.10.1 |
| tre-workspace-base | 1.2.3 |
| tre-workspace-unrestricted | 0.9.0 |

## 0.9.0 (February 9, 2023)

**BREAKING CHANGES & MIGRATIONS**:

* Move to Azure **Firewall Policy** ([#3107](https://github.com/microsoft/AzureTRE/pull/3107)). This is a major version for the firewall shared service and will fail to automatically upgrade. You should follow these steps to complete it:
  1. Let the system try to do the upgrade (via CI or `make all`). It will fail but it's fine since now we have the new version published and registered.
  2. Make a temporary network change with either of the following options:
      * Azure Portal: find your TRE resource group and select the route table resource (named `rt-YOUR_TRE_ID`).
        In the overview screen, find the `ResourceProcessorSubnet` (should be last in the subnet list), click on the `...` and select `Dissociate`.
      * Azure CLI:
        ```shell
        az network vnet subnet update --resource-group rg-YOUR_TRE_ID --vnet-name vnet-YOUR_TRE_ID --name ResourceProcessorSubnet --remove routeTable
        ```
  4. Issue a patch API request to `force-update` the firewall to its new version.

      One way to accomplish this is with the Swagger endpoint (/api/docs).
      ![Force-update a service](./docs/assets/firewall-policy-migrate1.png)

      If this endpoint is not working in your deployment - include `enable_swagger` in your `config.yaml` (see the sample file), or temporarily activate it via the API resource on azure (named `api-YOUR_TRE-ID`) -> Configuration -> `ENABLE_SWAGGER` item.
      ![Update API setting](./docs/assets/firewall-policy-migrate2.png)
  
  
  :warning: Any custom rules you have added manually will be **lost** and you'll need to add them back after the upgrade has been completed.

FEATURES:
* Add Azure Databricks as workspace service ([#1857](https://github.com/microsoft/AzureTRE/pull/1857))
* (UI) Added the option to upload/download files to airlock requests via Azure CLI ([#3196](https://github.com/microsoft/AzureTRE/pull/3196))

ENHANCEMENTS:
* Add support for referencing IP Groups from the Core Resource Group in firewall rules created via the pipeline ([#3089](https://github.com/microsoft/AzureTRE/pull/3089))
* Support for _Azure Firewall Basic_ SKU ([#3107](https://github.com/microsoft/AzureTRE/pull/3107)). This SKU doesn't support deallocation and for most non 24/7 scenarios will be more expensive than the Standard SKU.
* Update Azure Machine Learning Workspace Service to support "no public IP" compute. This is a full rework so upgrades of existing Azure ML Workspace Service deployments are not supported. Requires `v0.8.0` or later of the TRE project. ([#3052](https://github.com/microsoft/AzureTRE/pull/3052))
* Move non-core DNS zones out of the network module to reduce dependencies ([#3119](https://github.com/microsoft/AzureTRE/pull/3119))
* Review VMs are being cleaned up when an Airlock request is canceled ([#3130](https://github.com/microsoft/AzureTRE/pull/3130))
* Sample queries to investigate logs of the core TRE applications ([#3151](https://github.com/microsoft/AzureTRE/pull/3151))
* Remove support of docker-in-docker for templates/bundles ([#3180](https://github.com/microsoft/AzureTRE/pull/3180))
* API runs with gunicorn and uvicorn workers (as recommended) ([#3178](https://github.com/microsoft/AzureTRE/pull/3178))
* Upgrade core components and key templates to Terraform AzureRM ([#3185](https://github.com/microsoft/AzureTRE/pull/3185))

BUG FIXES:
* Reauth CLI if TRE endpoint has changed ([#3137](https://github.com/microsoft/AzureTRE/pull/3137))
* Added Migration for Airlock requests that were created prior to version 0.5.0 ([#3152](https://github.com/microsoft/AzureTRE/pull/3152))
* Temporarily use the remote bundle for `check-params` target ([#3149](https://github.com/microsoft/AzureTRE/pull/3149))
* Workspace module dependency to resolve _AnotherOperationInProgress_ errors ([#3194](https://github.com/microsoft/AzureTRE/pull/3194))
* Skip Certs shared service E2E on Friday & Saturday due to LetsEncrypt limits ([#3203](https://github.com/microsoft/AzureTRE/pull/3203))
* Create Workspace AppInsights via AzAPI provider due to an issue with AzureRM ([#3207](https://github.com/microsoft/AzureTRE/pull/3207))
* 'Workspace Owner' is now able to access Airlock request's SAS URL even if the request is not in review ([#3208](https://github.com/microsoft/AzureTRE/pull/3208))
* Ignore changes in log_analytics_destination_type to prevent redundant updates ([#3217](https://github.com/microsoft/AzureTRE/pull/3217))
* Add Databricks private authentication shared service for SSO ([#3201](https://github.com/microsoft/AzureTRE/pull/3201))
* Remove auth private endpoint from databricks workspace service ([3199](https://github.com/microsoft/AzureTRE/pull/3199))
* Fix DNS conflict in airlock-review workspace that could make the entire airlock module inoperable ([#3215](https://github.com/microsoft/AzureTRE/pull/3215))

COMPONENTS:

| name | version |
| ----- | ----- |
| devops | 0.4.5 |
| core | 0.7.4 |
| tre-shared-service-admin-vm | 0.3.0 |
| tre-shared-service-airlock-notifier | 0.4.0 |
| tre-shared-service-certs | 0.4.0 |
| tre-shared-service-cyclecloud | 0.4.0 |
| tre-shared-service-firewall | 1.0.0 |
| tre-shared-service-gitea | 0.5.0 |
| tre-shared-service-sonatype-nexus | 2.3.0 |
| tre-service-azureml | 0.7.26 |
| tre-user-resource-aml-compute-instance | 0.5.3 |
| tre-service-databricks | 0.1.72 |
| tre-workspace-service-gitea | 0.7.0 |
| tre-service-guacamole | 0.7.1 |
| tre-service-guacamole-export-reviewvm | 0.1.2 |
| tre-service-guacamole-import-reviewvm | 0.2.2 |
| tre-service-guacamole-linuxvm | 0.6.2 |
| tre-service-guacamole-windowsvm | 0.7.2 |
| tre-workspace-service-health | 0.1.1 |
| tre-service-innereye | 0.5.0 |
| tre-service-mlflow | 0.6.4 |
| tre-workspace-service-mysql | 0.3.3 |
| tre-workspace-airlock-import-review | 0.8.1 |
| tre-workspace-base | 1.1.0 |
| tre-workspace-unrestricted | 0.8.1 |

## 0.8.0 (January 15, 2023)

**BREAKING CHANGES & MIGRATIONS**:
* The model for `reviewUserResources` in airlock requests has changed from being a list to a dictionary. A migration has been added to update your existing requests automatically; please make sure you run the migrations as part of updating your API and UI.
  * Note that any in-flight requests that have review resources deployed will show `UNKNOWN[i]` for the user key of that resource and in the UI users will be prompted to deploy a new resource. [#2883](https://github.com/microsoft/AzureTRE/pull/2883)
* Env files consolidation ([#2944](https://github.com/microsoft/AzureTRE/pull/2944)) - The files /templates/core/.env, /devops/.env, /devops/auth.env are no longer used. The settings and configuration that they contain has been consolidated into a single file config.yaml that lives in the root folder of the project.
Use the script devops/scripts/env_to_yaml_config.sh to migrate /templates/core/.env, /devops/.env, and /devops/auth.env to the new config.yaml file.
* Upgrade to Porter v1 ([#3014](https://github.com/microsoft/AzureTRE/pull/3014)). You should upgrade all custom template definitions and rebuild them.

FEATURES:
* Support review VMs for multiple reviewers for each airlock request [#2883](https://github.com/microsoft/AzureTRE/pull/2883)
* Add Azure Health Data Services as workspace services [#3051](https://github.com/microsoft/AzureTRE/pull/3051)

ENHANCEMENTS:
* Remove Porter's Docker mixin as it's not in use ([#2889](https://github.com/microsoft/AzureTRE/pull/2889))
* Enable properties defined within the API to be overridden by the bundle template - enables default values to be set. ([#2576](https://github.com/microsoft/AzureTRE/pull/2576))
* Support template version update ([#2908](https://github.com/microsoft/AzureTRE/pull/2908))
* Update docker base images to bullseye ([#2946](https://github.com/microsoft/AzureTRE/pull/2946)
* Support updating the firewall when installing via makefile/CICD ([#2942](https://github.com/microsoft/AzureTRE/pull/2942))
* Add the ability for workspace services to request additional address spaces from a workspace ([#2902](https://github.com/microsoft/AzureTRE/pull/2902))
* Airlock processor function and api app service work with http2
* Added the option to disable Swagger ([#2981](https://github.com/microsoft/AzureTRE/pull/2981))
* Serverless CosmosDB for new deployments to reduce cost ([#3029](https://github.com/microsoft/AzureTRE/pull/3029))
* Adding disable_download and disable_upload properties for guacamole ([#2967](https://github.com/microsoft/AzureTRE/pull/2967))
* Upgrade Guacamole dependencies ([#3053](https://github.com/microsoft/AzureTRE/pull/3053))
* Lint TRE cost tags per entity type (workspace, shared service, etc.) ([#3061](https://github.com/microsoft/AzureTRE/pull/3061))
* Validate required secrets have value ([#3073](https://github.com/microsoft/AzureTRE/pull/3073))
* Airlock processor unit-tests uses pytest ([#3026](https://github.com/microsoft/AzureTRE/pull/3026))


BUG FIXES:
* Private endpoints for AppInsights are now provisioning successfully and consistently ([#2841](https://github.com/microsoft/AzureTRE/pull/2841))
* Enable upgrade step of base workspace ([#2899](https://github.com/microsoft/AzureTRE/pull/2899))
* Fix get shared service by template name to filter by active service only ([#2947](https://github.com/microsoft/AzureTRE/pull/2947))
* Fix untagged cost reporting reader role assignment ([#2951](https://github.com/microsoft/AzureTRE/pull/2951))
* Remove Guacamole's firewall rule on uninstall ([#2958](https://github.com/microsoft/AzureTRE/pull/2958))
* Fix KeyVault purge error on MLFlow uninstall ([#3082](https://github.com/microsoft/AzureTRE/pull/3082))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.4.4 |
| core | 0.5.2 |
| tre-shared-service-admin-vm | 0.3.0 |
| tre-shared-service-airlock-notifier | 0.3.0 |
| tre-shared-service-certs | 0.3.1 |
| tre-shared-service-cyclecloud | 0.4.0 |
| tre-shared-service-firewall | 0.7.0 |
| tre-shared-service-gitea | 0.5.0 |
| tre-shared-service-sonatype-nexus | 2.3.0 |
| tre-service-azureml | 0.6.0 |
| tre-user-resource-aml-compute-instance | 0.5.0 |
| tre-workspace-service-gitea | 0.7.0 |
| tre-service-guacamole | 0.7.0 |
| tre-service-guacamole-export-reviewvm | 0.1.0 |
| tre-service-guacamole-import-reviewvm | 0.2.0 |
| tre-service-guacamole-linuxvm | 0.6.1 |
| tre-service-guacamole-windowsvm | 0.6.0 |
| tre-workspace-service-health | 0.1.0 |
| tre-service-innereye | 0.5.0 |
| tre-service-mlflow | 0.6.0 |
| tre-workspace-service-mysql | 0.3.1 |
| tre-workspace-airlock-import-review | 0.6.0 |
| tre-workspace-base | 0.8.1 |
| tre-workspace-unrestricted | 0.6.0 |

## 0.7.0 (November 17, 2022)

**BREAKING CHANGES & MIGRATIONS**:
* The airlock request object has changed. Make sure you have ran the DB migration step after deploying the new API image and UI (which runs automatically in `make all`/`make tre-deploy` but can be manually invoked with `make db-migrate`) so that existing requests in your DB are migrated to the new model.
* Also the model for creating new airlock requests with the API has changed slightly; this is updated in the UI and CLI but if you have written custom tools ensure you POST to `/requests` with the following model:
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
* Support workspaces with multiple address spaces [#2808](https://github.com/microsoft/AzureTRE/pull/2808)
* Updated resource card in UI with visual improvements, disabled state badge and resource ID in info popout ([#2846](https://github.com/microsoft/AzureTRE/pull/2846))
* Add health information for backend services to UI info popout in footer ([#2846](https://github.com/microsoft/AzureTRE/pull/2846))


ENHANCEMENTS:
* Renamed several airlock fields to make them more descriptive and added a createdBy field. Included migration for backwards compatibility [#2779](https://github.com/microsoft/AzureTRE/pull/2779)
* Show error message when Review VMs are not configured in the current workspace
* CLI: Add missing endpoints and minor bug fixes ([#2784](https://github.com/microsoft/AzureTRE/pull/2784))
* Airlock Notifier: Provide a link to request in the UI in the email ([#2754](https://github.com/microsoft/AzureTRE/pull/2754))
* Add additional fields for Airlock Notification event ([#2798](https://github.com/microsoft/AzureTRE/pull/2798))
* Fail firewall database migration if there's no firewall deployed ([#2792](https://github.com/microsoft/AzureTRE/pull/2792))
* Added optional parameter to allow a client to retrieve a template by name and version ([#2802](https://github.com/microsoft/AzureTRE/pull/2802))
* Added support for `allOf` usage in Resource Templates - both across the API and the UI. This allows a template author to specify certain fields as being conditionally present / conditionally required, and means we can tidy up some of the resource creation forms substantially ([#2795](https://github.com/microsoft/AzureTRE/pull/2795)).
* As part of the above change, the `auto_create` string passed to the `client_id` field in each Workspace template has now moved to an `auth_type` enum field, where the user can select the authentication type from a dropdown.
* Adds extra dns zones and links into core network ([#2828](https://github.com/microsoft/AzureTRE/pull/2828)).
* Add UI version to its footer card ([#2849](https://github.com/microsoft/AzureTRE/pull/2849)).
* Use `log_category_types` in `azurerm_monitor_diagnostic_categories` to remove deprecation warning ([#2855](https://github.com/microsoft/AzureTRE/pull/2855)).
* Gitea workspace bundle has a number of updates as detailed in PR ([#2862](https://github.com/microsoft/AzureTRE/pull/2862)).

BUG FIXES:
* Show the correct createdBy value for airlock requests in UI and in API queries ([#2779](https://github.com/microsoft/AzureTRE/pull/2779))
* Fix deployment of Airlock Notifier ([#2745](https://github.com/microsoft/AzureTRE/pull/2745))
* Fix Nexus bootstrapping firewall race condition ([#2811](https://github.com/microsoft/AzureTRE/pull/2811))
* Handle unsupported azure subscriptions in cost reporting ([#2823](https://github.com/microsoft/AzureTRE/pull/2823))
* Redact secrets in conditional or nested properties ([#2854](https://github.com/microsoft/AzureTRE/pull/2854))
* Fix missing ID parameter in Certs bundle ([#2841](https://github.com/microsoft/AzureTRE/pull/2841))
* Fix ML Flow deployment issues and update version ([#2865](https://github.com/microsoft/AzureTRE/pull/2865))
* Handle 429 TooManyRequests and 503 ServiceUnavailable which might return from Azure Cost Management in TRE Cost API ([#2835](https://github.com/microsoft/AzureTRE/issues/2835))

COMPONENTS:
| name | version |
| ----- | ----- |
| devops | 0.4.2 |
| core | 0.4.43 |
| tre-workspace-base | 0.5.1 |
| tre-workspace-unrestricted | 0.5.0 |
| tre-workspace-airlock-import-review | 0.5.0 |
| tre-service-mlflow | 0.4.0 |
| tre-service-innereye | 0.4.0 |
| tre-workspace-service-gitea | 0.6.0 |
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
| tre-shared-service-airlock-notifier | 0.2.3 |
| tre-shared-service-admin-vm | 0.2.0 |
| tre-shared-service-certs | 0.2.2 |
| tre-shared-service-sonatype-nexus | 2.2.3 |
| tre-shared-service-firewall | 0.6.2 |

## 0.6.0 (October 24, 2022)

FEATURES:
* Added filtering and sorting to Airlock UI ([#2511](https://github.com/microsoft/AzureTRE/pull/2730))
* Added title field to Airlock requests ([#2503](https://github.com/microsoft/AzureTRE/pull/2731))
* New Create Review VM functionality for Airlock Reviews ([#2738](https://github.com/microsoft/AzureTRE/pull/2759) & [#2737](https://github.com/microsoft/AzureTRE/pull/2740))



ENHANCEMENTS:
* Add cran support to nexus, open port 80 for the workspace nsg and update the firewall config to allow let's encrypt CRLs ([#2694](https://github.com/microsoft/AzureTRE/pull/2694))
* Upgrade GitHub Actions versions ([#2731](https://github.com/microsoft/AzureTRE/pull/2744))
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

* GitHub Actions deployments use a single ACR instead of two. GitHub secrets might need updating, see PR for details. ([#2654](https://github.com/microsoft/AzureTRE/pull/2654))
* Align GitHub Action secret names. Existing GitHub environments must be updated, see PR for details. ([#2655](https://github.com/microsoft/AzureTRE/pull/2655))
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
* Using Porter's Terraform mixin 1.0.0-rc.1 where mirror in done internally ([#2677](https://github.com/microsoft/AzureTRE/pull/2677))
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
* UI - Initial implementation of Workspace Airlock Request View ([#2512](https://github.com/microsoft/AzureTRE/pull/2512))
* Add ability to automatically create Azure AD groups for each application role. Requires API version 0.4.30 or later ([#2532](https://github.com/microsoft/AzureTRE/pull/2532))
* Add `is_exposed_externally` option to Azure ML Workspace Service ([#2548](https://github.com/microsoft/AzureTRE/pull2548))
* Azure ML workspace service assigns Azure ML Data Scientist role to Workspace Researchers ([#2539](https://github.com/microsoft/AzureTRE/pull/2539))
* UI is deployed by default ([#2554](https://github.com/microsoft/AzureTRE/pull/2554))
* Remove manual/makefile option to install Gitea/Nexus ([#2573](https://github.com/microsoft/AzureTRE/pull/2573))
* Exact Terraform provider versions in bundles ([#2579](https://github.com/microsoft/AzureTRE/pull/2579))
* Stabilize E2E tests by issuing the access token prior using it, hence, reducing the change of expired token ([#2572](https://github.com/microsoft/AzureTRE/pull/2572))

BUG FIXES:

* API health check is also returned by accessing the root path at / ([#2469](https://github.com/microsoft/AzureTRE/pull/2469))
* Temporary disable AppInsight's private endpoint in base workspace ([#2543](https://github.com/microsoft/AzureTRE/pull/2543))
* Resource Processor execution optimization (`porter show`) for long-standing services ([#2542](https://github.com/microsoft/AzureTRE/pull/2542))
* Move AML Compute deployment to use AzApi Terraform Provider ([#2555](https://github.com/microsoft/AzureTRE/pull/2555))
* Invalid token exceptions in the API app are caught, throwing 401 instead of 500 Internal server error ([#2572](https://github.com/microsoft/AzureTRE/pull/2572))

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

* MySQL workspace service ([#2476](https://github.com/microsoft/AzureTRE/pull/2476))

ENHANCEMENTS:

* 'CreationTime' field was added to Airlock requests ([#2432](https://github.com/microsoft/AzureTRE/pull/2432))
* Bundles mirror Terraform plugins when built ([#2446](https://github.com/microsoft/AzureTRE/pull/2446))
* 'Get all Airlock requests' endpoint supports filtering ([#2433](https://github.com/microsoft/AzureTRE/pull/2433))
* API uses user delegation key when generating SAS token for airlock requests ([#2460](https://github.com/microsoft/AzureTRE/pull/2460))
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

