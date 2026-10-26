# End-to-end (E2E) tests

## Prerequisites

1. Authentication and Authorization configuration set up as noted in the [Authentication documentation](../tre-admins/auth.md)
1. An Azure Tre deployed environment.

## Registering bundles to run End-to-end tests

End-to-end tests depend on certain bundles to be registered within the TRE API.

When End-to-end tests run in CI, they are registered as a prerequisite to running tests.

When running tests locally, use the `prepare-for-e2e` Makefile target:

```cmd
make prepare-for-e2e
```

## Certificate lifecycle tests

Use a TRE without Nexus for tests that remove and reinstall the certificate shared service.
Removing its certificate can interrupt Nexus.
Run only one certificate lifecycle test suite per TRE at a time.
Do not run it alongside Airlock or shared-service tests that use the same certificate service.
Use the same hostname and certificate name when testing reuse after reinstallation.

## Debugging the End-to-End tests

Use the "Run and Debug" panel within Visual Studio Code, select "E2E Extended", "E2E Smoke" or "E2E Performance" in the drop down box and click play.

- This will copy `config.yaml` settings to `/workspaces/AzureTRE/e2e_tests/.env` for you which supplies your authentication details

- This will also use `/workspaces/AzureTRE/core/private.env` file for other values.

If an E2E test fails while waiting for an operation, check its test log.
Use the timestamp and operation ID to find the matching API logs.

If an operation poll gets an unexpected HTTP status, the test logs the UTC time, the operation path, the status and the `request-id` header of the response.
The API puts the trace of each request in this header as `|<trace ID>.<span ID>.`, also for HTTP 500.
App Insights stores the trace ID as `OperationId`. Run this query in the Log Analytics workspace of the environment:

```kusto
union AppRequests, AppExceptions, AppTraces
| where OperationId == "<trace ID>"
| order by TimeGenerated asc
```

## Airlock draft deletion

The draft-deletion case requires AzureCloud, `ARM_SUBSCRIPTION_ID`, `TRE_ID` and the existing CI Azure login.
The CI identity must have ARM read access to blob containers in the TRE Airlock storage account.
Local runs use the Azure CLI login. CI uses its existing federated identity. The test does not add permissions.

After submission, the test checks that the old draft SAS cannot write a new blob.
A `ContainerNotFound` or `AuthorizationPermissionMismatch` response must also have independent ARM evidence:
the draft is absent, and the submitted container exists with matching workspace and import-stage metadata.
A permission error alone cannot pass the test. Other storage errors and ARM lookup failures remain test failures.
These checks share a 60-second deadline. They do not compare submitted file contents. The review-VM lifecycle test also does not verify file contents.

## Validate one bundle

The [bundle coverage map](https://github.com/microsoft/AzureTRE/blob/main/e2e_tests/bundle_coverage.json) lists every Porter bundle, its prerequisite bundles, exact pytest cases and remaining coverage gaps.
Selecting a bundle runs only its declared cases. Fixtures may deploy prerequisite resources.
A passing case does not prove the bundle's full functional, upgrade or custom-action lifecycle.

### Check selection without deploying

Use the E2E Python environment from the repository root:

```bash
python3 e2e_tests/run_bundle.py --bundle tre-workspace-service-azuresql --collect-only
```

This collects `test_azuresql.py::test_sql_query_survives_sku_upgrade` without creating resources.
The case checks a private SQL query and data persistence after an S1-to-S2 SKU change.

The report records `not_run`, even when collection succeeds.
Unknown names, unavailable cases, missing tests and unexpected collected cases fail explicitly.

### Run against a configured environment

After configuring the prerequisites above, run:

```bash
TEST_BUNDLE=tre-workspace-service-azuresql make test-e2e-bundle
```

Use one test process. Per-bundle runs reject a marker expression or multiple workers.
If the selection includes the Guacamole AAD case, clear `TEST_AAD_WORKSPACE_ID`.
That case requires an owned workspace so cascade cleanup removes its new service.
Some shared-service cases replace existing services, so use an isolated validation environment.
Check the selected entry's prerequisites and limitations before running it.

### OpenAI selection

Select `tre-workspace-service-openai` to run `test_openai.py::test_private_openai_lifecycle`.
The branch workflow registers the OpenAI bundle. The test also replaces its generic case in the `workspace_services` group.
The test requests `gpt-5.1 | 2025-11-13`, private access and one regional `Standard` capacity unit.
It does not switch models or deployment types when Azure cannot satisfy those inputs.

The prerequisite check uses the workspace resource group's actual region and the current subscription model and usage APIs.
It requires a generally available chat model, a current Standard tier and at least one free capacity unit.
It rejects retired model/tier dates, fine-tuning quotas and incomplete or blocked quota data.
The CI identity needs permission to read model and quota data at subscription scope.
The check does not grant roles or reserve capacity. Azure deployment can still fail after it passes.

Prerequisite failures fail the selected test before service creation. They do not count as skipped or passing coverage.
Service creation has a 45-minute deadline. Verification has a separate five-minute deadline.
Failed creation and teardown use the existing helper's separate cleanup deadline.
A configured workspace is retained. A fixture-created workspace uses the fixture's cleanup.
Private inference, access control, upgrades and complete physical cleanup remain separate checks.

### Certificate and Nexus selection

Select `tre-shared-service-certs` to install, uninstall and reinstall the certificate shared service with the same hostname and certificate name.
The case requires certificate bundle version `0.9.0` or later and pins both installations to the selected template version.
It checks the deployed API record, the gateway's public certificate SAN and validity, and the gateway's stopped state.
Reinstallation must preserve the SHA-256 certificate fingerprint and produce a matching resource processor reuse log without issuance evidence.
After each uninstall, the case requires API HTTP 404 and ARM confirmation that the gateway, public IP and challenge storage are absent.
The bundle report records public metadata, reuse and cleanup results. It does not require Nexus EULA consent.

The evidence helper currently supports `AzureCloud`. It uses the existing deployment identity for ARM and Log Analytics access.
If the gateway omits public certificate data, the helper reads the exact referenced certificate version through the resource-processor VM.
This uses a temporary managed Run Command and the VM's existing identity and private network access.
The deployment identity must be able to create, read and delete that command on the resource-processor VM.
The helper removes the command after success, failure or cancellation. It reads public certificate data only, without changing vault access or permissions.
Log evidence is limited to the installation's message spans, so other installations in the same trace cannot affect the result.
Only aggregate log counts enter the test process. Missing, partial or delayed evidence beyond the deadline fails the case.
See [Key Vault public certificate retrieval](https://learn.microsoft.com/en-us/rest/api/keyvault/certificates/get-certificate/get-certificate)
and [Azure Monitor query authentication](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/api/access-api).

Each installation has a 45-minute provisioning deadline. Cleanup has its own 60-minute deadline.
The complete case has a 285-minute limit, leaving 15 minutes within the five-hour bundle job for setup and reporting.
It refuses to change resources when Nexus is present. Existing certificate resources must belong to earlier E2E tests before recovery can remove them.
Cleanup has a separate deadline and retains the certificate service if Nexus appears before deletion.
Use an isolated environment and run mutating suites sequentially. These guards do not provide a distributed lock.

Select `tre-shared-service-sonatype-nexus` to run the existing certificate/Nexus lifecycle case.
The report identifies certificates and the deployed firewall as prerequisites. Dependency creation does not complete their separate evidence records.
Nexus selection still requires explicit EULA consent. Both selections retain the weekend certificate rate-limit precaution.
After checking rate limits, use `runCertificateTestsOnWeekends=true` in the branch workflow or `TEST_RUN_CERTIFICATE_TESTS_ON_WEEKENDS=true` locally.
A skipped case remains unproven coverage.

The certificate-only case is opt-in through bundle selection or the `certificate_validation` marker.
It is excluded from the ordinary `shared_services` selection to avoid an additional certificate request in that suite.
The existing combined case remains in that suite. It deletes Nexus before its certificate dependency.
Certificate chain validation, actual renewal, retained Key Vault artefacts, Nexus package/proxy use, upgrades and other Azure resource removal need separate evidence.
The case does not purge certificates. A first installation can reuse a certificate retained by an earlier run.

Before merging the certificate fix, run this case from a trusted upstream branch that contains both the certificate implementation and these tests.
Select `e2eBundle=tre-shared-service-certs` in `deploy_tre_branch.yml` and leave the marker selector empty.
PR slash commands use workflow definitions from `main`. `/test` runs smoke tests and `/test-shared-services` excludes this certificate-only case.
A test-only PR without the new certificate bundle cannot validate reuse. Run Nexus and Airlock only after this case and its cleanup pass.

### Linux VM selection

Select `tre-service-guacamole-linuxvm` to run `test_guacamole_linuxvm.py::test_create_guacamole_linux_vm`.
The case creates a Linux VM and waits for its Nexus-backed bootstrap. Thus the run needs a suitable Nexus instance or `acceptNexusEula=true`.
The case then runs the `stop`, `start` and `reset_password` actions.
After `stop` and `start`, the case reads the VM power state from Azure. After `reset_password`, it makes sure that the Key Vault secret has a new version.
The case does not sign in to the VM, so it does not prove interactive access or the new password.

### Base workspace lifecycle

Select `tre-workspace-base` to run `test_workspace_base.py::test_base_workspace_lifecycle` independently.
The case always creates its own workspace with Automatic authentication and backups disabled. It does not reuse `TEST_WORKSPACE_ID`.
It checks the deployed record and uses the configured workspace identity to list the new workspace's services.
It then disables and deletes the workspace, waits for the delete operation and confirms that an API lookup returns HTTP 404.
Body failures still trigger cleanup. If cleanup also fails, the original failure is preserved with an additional diagnostic note.

Setup uses the existing one-hour deployment limit and failed-create recovery. The API checks have a five-minute limit.
Cleanup has a separate one-hour budget. The case is opt-in through bundle selection or the `workspace_validation` marker.
It does not add another workspace to the extended suite.

These checks do not prove network isolation, storage access, upgrades, custom actions or backup restore and retention.
Verify Azure resource removal separately when recording release evidence.

### SQL time limits

The SQL bundle job has a 300-minute limit. Its first step sets an absolute lifecycle deadline at 270 minutes.
Setup and queries stop with 120 minutes remaining for cleanup. Container startup uses the same budget.
The SQL case manages its own workspace and Guacamole service so that setup and cleanup share this deadline.
It preserves pre-created resources and divides the remaining cleanup time between the resources it created.
Failed-create recovery and temporary probe cleanup also count towards the lifecycle deadline.
The final 30 minutes are reserved for results and job overhead. Cleanup failures still fail the test.
For a local run, the 270-minute lifecycle budget starts when the SQL case begins.

### MySQL selection

Select `tre-workspace-service-mysql` to run `test_mysql.py::test_private_mysql_query_survives_sku_change`.
The case creates its own workspace, Guacamole service, Linux VM and MySQL service.
The Linux VM installs the MySQL client through Nexus. Thus the run needs a suitable Nexus instance or `acceptNexusEula=true`.
The case writes a row through private DNS with the Burstable SKU. It then changes the SKU to General Purpose and reads the row again.
The VM reads the administrator password from the workspace Key Vault through a temporary role assignment on that secret only.
The MySQL job uses the SQL time limits above with its own `MYSQL_VALIDATION_DEADLINE`. If the case creates Nexus, it removes Nexus after the VM.
These checks do not prove previous-version upgrades or researcher access.

### Gitea selection

Select `tre-workspace-service-gitea` to run `test_gitea.py::test_private_gitea_repository_survives_update`.
The case creates its own workspace, Guacamole service, Windows VM and Gitea service.
It gives the VM identity a temporary Key Vault Secrets User role on the secret that holds the Gitea admin password.
From the VM, the case makes sure that the Gitea host resolves to a private address and that the Gitea API is available.
It also makes sure that Gitea rejects a repository create without credentials (HTTP 401) and a request with a wrong password (HTTP 401).
The VM then creates a private repository with the admin account and commits a file. An anonymous read of the repository gets HTTP 404.
An update changes the display name. Then the case gives the web app a new OIDC client ID.
The start script must stop Gitea one time for the new OIDC settings, and App Service must start it again.
Then the case stops and starts the web app. The VM reads the file again and deletes the repository.
Then the case makes sure that the web app resolves its three Key Vault references, for the admin password, the OIDC client secret and the database password.
It also counts lines in the web app console log in the TRE Log Analytics workspace. No line can show a password, a client secret or a new access token.
The count waits for the start script lines of the start after the stop, and then for two more minutes, because the lines of one start can arrive at different times.
The last start has the same OIDC settings, so the log must show only one stop for the new OIDC settings.
The query returns counts only. The CI identity needs read access to the Log Analytics workspace.
At the end, the case makes sure that the web app and MySQL have public network access disabled, and that the storage firewall denies by default.
The Gitea job uses the SQL time limits with its own `GITEA_VALIDATION_DEADLINE`.

### Health selection

Select `tre-workspace-service-health` to run `test_health.py::test_private_fhir_access_and_dicom_update`.
The case creates its own workspace, Guacamole service, Windows VM and Health service with FHIR R4.
The Health bundle needs the workspace owners group, and only an Automatic workspace gets Entra ID groups.
So the case always creates an Automatic workspace. It does not use `TEST_WORKSPACE_ID`, `TEST_WORKSPACE_SERVICE_ID` or `TEST_WORKSPACE_APP_ID`.
From the VM, the case makes sure that the FHIR host resolves to a private address and that the FHIR metadata is available.
If the FHIR name lookup fails, the case runs that probe again after 60 seconds, 3 attempts in total. Before this lookup, the probe changes no data.
It also makes sure that FHIR rejects a data request without a token (HTTP 401) and from an identity without a role (HTTP 403).
The case then gives the VM identity a temporary FHIR Data Contributor role on the FHIR service and writes a Patient.
The role can take some minutes to apply, so the probe waits up to 10 minutes for a first HTTP 200.
Until the end of this wait, the probe sends the create again after HTTP 403 or 429.
It sends the search again after HTTP 403, 429, 500, 502, 503 or 504.
If a probe fails, the test error gives the stage and the HTTP status of the failed request.
An update adds DICOM. The case makes sure that the update kept the private endpoint.
It then reads the Patient again and makes sure that the DICOM host is private and needs a token.
At the end, the case sends FHIR and DICOM requests without a token from the test runner, outside the workspace network.
Azure must reject each request with HTTP 403. The case tries again for up to 5 minutes, because Azure can take this time to block public traffic.
The case then reads the healthcare workspace and DICOM again, and makes sure that each has public network access disabled.
The case does not read this value on FHIR, because the bundle does not set it.
FHIR from Health 1.0.0 reports `Disabled`, but FHIR from Health 0.3.8 reports `Enabled`, also after a request sets `Disabled`.
The Health job uses the SQL time limits with its own `HEALTH_VALIDATION_DEADLINE`.

### Backup restore and delete

Set `e2eTestsCustomSelector` to `backup_retention` or `backup_deletion` to run one case of `test_backup_restore.py::test_file_share_restore_and_workspace_delete`.
Run one case in each workflow run, because each case can take 2 hours. The marker `backup_validation` selects both cases.
Each case creates its own workspace with `enable_backup` on, a Guacamole service and a Windows VM.
The `retain` case sets `delete_backups_on_uninstall` to `false`, and the `delete` case sets it to `true`.
From the VM, the case makes sure that the host of the workspace file share is private and that the VM identity without a role gets HTTP 403.
The case then gives the VM identity a temporary Storage File Data Privileged Contributor role on the workspace resource group. The VM writes a file through the Azure Files REST API.
The role is not on the share, because the Azure Backup delete lock on the storage account also blocks the delete of a role assignment on the share.
An on-demand Azure Backup job makes a recovery point. The VM changes the file, a restore of that file from the recovery point follows, and the VM reads the original content again.
The case then deletes the VM, the Guacamole service and the workspace. Each delete must pass.
After the `delete` case, the workspace resource group must be gone.
After the `retain` case, the vault must keep the stopped item with its recovery point, and the storage account must keep its share and deny public network access.
A second restore from the recovery point must pass.
The last clean-up step turns off soft delete, deletes the item and the vault, and deletes the retained resource group.
Azure does not let a request turn off soft delete in some vaults, for example in a vault with enhanced security.
If Azure keeps soft delete on, the deleted backup data stays for 14 days, and Azure does not delete the vault before that.
The step then deletes the backup data and the storage account, and it adds the tag `e2e_delete_after` with a date to the resource group.
Delete the resource group by hand after that date.
This step runs after the workspace delete, also when the case fails earlier. It runs only if the API deleted the workspace, so a failed delete stays for diagnosis.

### Airlock v1 to v2 move

Set `e2eTestsCustomSelector` to `airlock_migration_validation` to run `test_airlock_migration.py::test_legacy_airlock_workspace_moves_to_v2`.
The core must have `enable_legacy_airlock` set to `true`, and the test identity must have `WorkspaceOwner` and `AirlockManager` on the manual test workspace application.
The case follows the steps in [Legacy Airlock Architecture](../azure-tre-overview/airlock-legacy.md#upgrading-to-current-architecture):

1. It creates a Manual workspace with `airlock_version` set to `1`. An import uses the legacy external account and is approved.
1. It calls `POST /migrations` two times. The workspace keeps `airlock_version` `1`.
1. With an import draft in progress, a change to `airlock_version` `2` must get HTTP 400. The case then cancels the draft.
1. The five legacy storage accounts of the workspace must exist with the default network action `Deny`.
1. The change to `2` must pass. A new import draft must use the consolidated core account and a `-draft` container.
1. The legacy request keeps its record, its `approved` status and `airlock_version` `1`.
1. The five legacy storage accounts of the workspace must not exist. So the stored files of the legacy request are deleted, as the docs say.
1. A change back to `1` must get HTTP 400.

### Airlock upgrade from an earlier release

The two cases in `test_airlock_upgrade.py` follow the procedure in [Legacy Airlock Architecture](../azure-tre-overview/airlock-legacy.md#upgrading-to-current-architecture) with a workspace that an earlier release created. Both cases need the manual test workspace application with `WorkspaceOwner` and `AirlockManager`.

1. Deploy the earlier release, for example `v0.29.1`, and set `e2eTestsCustomSelector` to `airlock_upgrade_seed`. The case creates the workspace `E2E Airlock upgrade seed` with an approved legacy import, and keeps it.
1. Deploy the current code to the same environment with `enable_legacy_airlock` set to `true`. The deployment runs `POST /migrations`.
1. Set `e2eTestsCustomSelector` to `airlock_upgrade_verify`. The case makes sure that the core legacy accounts still exist and that the workspace has `airlock_version` `1`.
1. The case upgrades the workspace to the current `tre-workspace-base` version. The legacy workspace accounts must still exist with the default network action `Deny`, and a new legacy import must pass.
1. The case changes `airlock_version` to `2`. The legacy workspace accounts must not exist, the legacy requests keep their records, and a new import draft must use the v2 core account.
1. The case deletes the workspace.
1. If no other workspace uses Airlock v1, set the variable `ENABLE_LEGACY_AIRLOCK` of the GitHub environment `CICD` to `false`. Deploy the current code again with `e2eTestsCustomSelector` set to `airlock and not airlock_validation`. Terraform deletes the five legacy core accounts, and the Airlock cases must pass on v2.
1. Delete the variable `ENABLE_LEGACY_AIRLOCK`. The next deployments then use the default value `true`.

The `v0.29.1` OHDSI image does not build, because `deb.debian.org` no longer has the Debian 11 security packages. Before you deploy `v0.29.1`, add the fix from [#5090](https://github.com/microsoft/AzureTRE/pull/5090) to the branch of the earlier release.

### Run the branch workflow before merge

1. Push the reviewed changes to a branch in `microsoft/AzureTRE`.
2. Select that branch in **Deploy Azure TRE (branch)**.
3. Set `e2eBundle` to the exact Porter bundle name.
4. Leave `e2eTestsCustomSelector` empty and set `e2eProcesses` to `1`.
5. Keep `skipDeployment` false for a new branch environment.

The workflow validates selection before deployment. It passes the bundle name as data in a JSON request, rather than embedding it in shell code.
Prepared requests require every generated metadata field, a full checkout SHA and non-empty TRE, location and cloud identifiers.
The test runner rejects incomplete requests and mismatches with the current checkout or configured TRE, location and cloud.
Unknown fields are ignored. Workflow metadata may be empty outside GitHub Actions.
Branch and PR-comment references derive different environment IDs. A completed test run does not remove its core environment.

Bundle tests run in a separate job. Marker selections use the existing sequential test groups.
Both paths publish their results to the workflow summary.

Existing slash commands retain their marker-based behaviour. They load workflow definitions from `main`; new branch-workflow inputs do not require merging first.

### Read the evidence

The **E2E Test Results (Bundle)** artefact contains:

- `pytest_e2e_bundle.xml`: test, failure, skip and teardown results.
- `bundle-validation.json`: requested bundle, source version, declared prerequisite versions, requested and collected cases, coverage limitations, commit/workflow provenance, environment identity and observed resource/operation IDs.

The JSON report copies only selected identifiers and operation states. It excludes resource properties, tokens and failure tracebacks.
Source versions describe the checked-out manifests; verify deployed versions separately when reusing an environment.
A test can call `record_deployed_resource` for a resource that it reads. The report then has a `deployed_template_version` record for that resource.
`passed_selected_cases` means the selected assertions and their teardown passed. The report always leaves `full_lifecycle_proven` false for a separate evidence review.
An entirely skipped selection exits unsuccessfully. Individual skipped cases retain their reasons, and a mixed pass/skip result is marked `partial`.

Unavailable bundles fail with the gap recorded in the map. Adding a selector does not implement missing tests or fix bundle publication and registration gaps.

### CycleCloud server validation

Select `tre-shared-service-cyclecloud` with the branch workflow's bundle input, or use:

```bash
TEST_BUNDLE=tre-shared-service-cyclecloud make test-e2e-bundle
```

Use a dedicated AzureCloud environment with one writer and no existing CycleCloud service or DNS zone.
Publish and register the checkout firewall and CycleCloud bundles. Deploy the firewall before validation.
Register the CycleCloud bundle, version 1.0.0 or later, with `start` and `stop` actions.
Accept the CycleCloud server image terms separately before the run. The test reads the agreement and regional image list. It does not accept terms.
Check `Standard_D4s_v5` capacity and quota in the core region before deployment. Image availability does not prove VM capacity.

The case creates one server and checks its private VM address, DNS configuration, blob private endpoint, managed identity and firewall rules.
It also checks the network security group of the VM network card. By default, the inbound allow rules must be for the core address space and the `AzureLoadBalancer` service tag only, and the lowest-priority rule must deny other `VirtualNetwork` traffic.
It invokes stop/start through TRE and verifies the VM power states. It changes the overview to exercise a same-version Terraform upgrade and checks that the VM identity remains stable.
The same update sets `cluster_address_spaces` to one test range outside the core address space. The test then checks that the TCP 9443 rule allows exactly that range.
The test records the existing firewall as reused. Smoke completes before the bundle job starts.

The job sets `CYCLECLOUD_VALIDATION_DEADLINE` before container setup. The test reserves 120 minutes for cleanup within its 270-minute deadline.
It owns an accepted service before polling. Cleanup waits for terminal operations, verifies ownership and then uses TRE deletion.
It verifies removal of the VM, disk, NIC, network security group, storage, blob private endpoint, DNS zone and captured identity's roles. It also checks that the original firewall rules are restored.
Failed cleanup fails the test. Core Key Vault credentials can remain soft-deleted. The test does not retrieve or purge them.

This case does not configure the CycleCloud application or create an HPC cluster. Browser access, application TLS trust, private DNS reachability and prior-release upgrades remain unproven.
The case reads the network rules from Azure Resource Manager. It does not send traffic from a workspace to the server.
The existing bundle grants subscription Contributor to its VM and permits SharedSubnet access to ARM and GitHub. It does not disable the storage public endpoint.
A private endpoint and a successful server lifecycle do not prove workspace isolation or storage access restrictions.

### Private OHDSI validation

Select the bundle from a branch that contains its repaired bootstrap and validation case:

```bash
TEST_BUNDLE=tre-workspace-service-ohdsi make test-e2e-bundle
```

Use a dedicated AzureCloud environment with one writer and matching deployment and authentication tenants.
Publish and register the checkout base-workspace, firewall and OHDSI bundles. Deploy the firewall before the test.
Check PostgreSQL 14 capacity for `B_Standard_B1ms`, 32 GiB storage and availability zone 1 in the selected region.
The case creates a fresh Automatic workspace. It disables backups and sets `configure_data_source=false` without data-source properties.

The case checks both private web apps, their pinned images and PostgreSQL networking.
It also checks that the WebAPI identity has a role on each of its five Key Vault secrets and no role on the vault, and that each Key Vault reference resolves.
Successful installation includes the bundle's private WebAPI readiness check and local administrator setup.
A metadata update exercises a same-version upgrade. The test checks the callback and firewall collections after each operation.
It waits for terminal operations before updates or deletion. It owns accepted resources before evidence writes or client closure.

The job sets `OHDSI_VALIDATION_DEADLINE` before container setup. The case reserves 120 minutes for cleanup within 270 minutes.
Cleanup removes the service before its workspace. It checks Azure resource removal, app DNS records, callback removal and firewall restoration.
If service cleanup fails, the case retains the workspace and fails. The shared core PostgreSQL DNS link remains in place.
Key Vault items can remain soft-deleted under the existing retention policy.

Browser sign-in, independent private HTTP and DNS probes, database data persistence and previous-version upgrades remain unproven.
Synapse provisioning, CDM queries and clinical workflows need separate cases. Retained non-empty data-source properties are outside this case.
The Synapse script does not currently inspect `configure_data_source`; empty properties avoid that path.
