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

## Debugging the End-to-End tests

Use the "Run and Debug" panel within Visual Studio Code, select "E2E Extended", "E2E Smoke" or "E2E Performance" in the drop down box and click play.

- This will copy `config.yaml` settings to `/workspaces/AzureTRE/e2e_tests/.env` for you which supplies your authentication details

- This will also use `/workspaces/AzureTRE/core/private.env` file for other values.

## Investigate operation-polling failures

Unexpected HTTP responses fail operation polling. HTTP 500 is not retried or treated as successful deletion.
The error log records a UTC timestamp, method, recognised operation path, status, media type, body size and coarse body classification.
It includes allowlisted correlation headers only when their values match supported identifier formats.
Unrecognised paths and header values are omitted or redacted. The diagnostic record excludes response bodies, credentials, host names and URL parameters.

If a poll fails, use its timestamp, operation ID and available correlation IDs to find the API exception and App Service request record.
Check API exception telemetry before a validation run. Record terminal resource deletion separately from the failed poll.
These diagnostics help investigate the failure. They do not establish its cause or guarantee that server telemetry is available.

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
Some shared-service cases replace existing services, so use an isolated validation environment.
Check the selected entry's prerequisites and limitations before running it.

### Export review-VM selection

Select `tre-service-guacamole-export-reviewvm` to run `test_airlock_export_review.py::test_airlock_export_review_vm_flow`.
This case is opt-in. It is not part of `airlock` or `airlock_validation`, so existing Airlock jobs do not acquire another VM lifecycle.
Use the separate bundle job with one process and run other mutating suites sequentially.

The case requires AzureCloud and a configured manual test workspace application.
The test identity must have both `WorkspaceOwner` and `AirlockManager` on that application.
The CI identity needs VM read and managed Run Command permissions for the test resources.
Use an enabled Nexus 3.11.0 or newer, or explicitly accept its EULA so the existing prerequisite helper can create it.
The test does not add role assignments or network access rules.

The case creates a separate workspace, Guacamole service and minimal Windows upload VM.
It ignores configured workspace and service IDs and preserves any reused Nexus and certificate services.
The upload VM sends one synthetic blob to the export draft through the workspace private endpoint.
The SAS is a protected Run Command parameter. The probe does not print it.
After the request reaches `in_review`, the case creates an export review VM in the same workspace.
It checks the downloaded file's hash before approval, then waits for automatic VM deletion.
Both VM bundle versions must match the checkout. The evidence report records their observed versions.
Recovery cleanup cannot turn failed automatic deletion into a passing result.

The bundle job sets a 270-minute absolute deadline before container startup.
Provisioning and validation stop with 120 minutes reserved for cleanup, within the 300-minute job limit.
Local runs start that budget when the case begins. Failed setup and probes also trigger bounded cleanup.
Each owned resource receives a share of the remaining cleanup time, so one stalled delete cannot consume the entire reserve.
The case removes its VMs, service and workspace before releasing its Nexus prerequisites.
Interactive desktop access, denied access, rejected exports, upgrades, custom actions and physical resource removal need separate evidence.

### Databricks selection

Select `tre-shared-service-databricks-private-auth` for the authentication service lifecycle.
Select `tre-service-databricks` for its authentication prerequisite, a new base workspace and the private Databricks service.
The branch workflow already publishes and registers both bundles. It completes smoke tests before starting the selected bundle job.
Use one test process and one writer in a dedicated environment.
Do not run these cases alongside smoke fixtures, other bundle tests, workspace deployments or manual resource changes.

Both cases require AzureCloud, matching Azure and authentication tenants, and the existing CI Azure identity.
Preflight requires no TRE workspaces, no authentication service and no records other than SOA in the core Databricks private DNS zone.
It checks core resource ownership and the required network/DNS resources before creating anything.
The workspace-service case also requires the checkout version of the deployed firewall bundle and complete endpoint data for the core region.
The checks use the actual core resource group location. Configured workspace IDs are not reused.

The authentication private endpoint is shared by workspaces in the same region and private DNS zone.
Deleting it can break their browser sign-in. See [Databricks Private Link concepts](https://learn.microsoft.com/en-us/azure/databricks/security/network/concepts/private-link).
The tests create and remove only owned resources. They recheck isolation before authentication removal and retain it if dependent cleanup fails.
These checks do not provide an atomic lock against another writer. Clean up a failed isolated run before trying again.

The tests compare registered and deployed versions with the checkout. ARM checks cover resource identity, ownership tags,
private access, managed identity, injected subnets, private endpoints and their DNS configuration.
Cleanup checks TRE removal and the declared ARM resources. The workspace-service case also checks removal of its firewall rule collections.
The service pipeline upgrades its parent VNet and changes the shared firewall, which is why it requires exclusive use.
The total deadline is 270 minutes, including a 120-minute cleanup reserve. The workflow starts that deadline before container setup.

Browser sign-in, private DNS reachability, cluster and notebook execution, user access and previous-version upgrades remain unproven.
Neither bundle defines custom actions. Endpoint completeness checks do not establish that every regional endpoint is current.
Switzerland North's previously empty storage and Event Hubs lists are corrected using the
[documented regional endpoints](https://learn.microsoft.com/en-us/azure/databricks/resources/ip-domain-region).
The current DBFS storage name contains only the last four characters of the service ID, so a global name collision can still prevent deployment.

### Azure ML selection

Select `tre-service-azureml` for the private parent-service case.
Select `tre-user-resource-aml-compute-instance` for the assigned compute case and its parent prerequisites.
The branch workflow publishes the compute bundle and registers it after Azure ML.
For local execution, build, publish and register the base workspace, Azure ML service and compute bundle first.
Use the separate bundle job with one process and run mutating suites sequentially.

Both cases create an Automatic workspace and require non-empty owner and researcher group IDs.
They ignore configured workspace and service IDs. The old generic Azure ML case is replaced by the focused parent selection.
The test identity needs the existing Automatic-workspace permissions. Automatic workspace group creation must be enabled.
ARM inspection currently supports AzureCloud and requires matching authentication and Azure tenants.

For compute, set the environment variable `TEST_AML_USER_OBJECT_ID` to an existing Entra user's object ID.
In GitHub Actions, set the same name as a variable on the selected GitHub environment.
Do not use an application or service-principal object ID.
Preflight checks UUID syntax. It does not query the directory or establish the user's type, existence or access.
The test does not read Graph, grant roles or add group membership.
The assigned user still needs the normal workspace access before a separate interactive test.

The compute case explicitly requests `Standard_D2_v3`. Check regional capacity and AML quota before execution.
The test checks the deployed bundle versions, exact ARM IDs, TRE ownership tags, private subnet, disabled public IP and assigned user.
It waits for the compute to reach `Running`. It removes compute before the service and workspace, and checks TRE and ARM removal.
The parent case checks successful private AML workspace provisioning and removal.
These ARM checks follow the [compute response contract](https://learn.microsoft.com/en-us/rest/api/azureml/compute/get).

The bundle job sets a 270-minute absolute deadline before container startup, with 120 minutes reserved for cleanup.
Cleanup runs in reverse dependency order and divides the remaining time among owned resources.
Local runs start the same budget when the case begins. Failed provisioning and verification still trigger bounded cleanup.
Missing prerequisites and failed assertions fail the case. They do not count as skipped or passing coverage.

These cases do not prove notebook execution, interactive user access, prior-version upgrades or deletion of every dependent Azure artefact.
The compute bundle defines no custom actions. Retain these limits in each bundle's evidence record.

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

Select `tre-shared-service-certs` to create and delete only the certificate shared service.
The case checks the deployed API record and confirms HTTP 404 after deletion. It does not require Nexus EULA consent.
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
Certificate content, renewal, retained Key Vault artefacts, Nexus package/proxy use, upgrades and physical resource removal need separate evidence.

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
Register the repaired CycleCloud bundle, version 0.7.10 or later, with `start` and `stop` actions.
Accept the CycleCloud server image terms separately before the run. The test reads the agreement and regional image list. It does not accept terms.
Check `Standard_DS3_v2` capacity and quota in the core region before deployment. Image availability does not prove VM capacity.

The case creates one server and checks its private VM address, DNS configuration, blob private endpoint, managed identity and firewall rules.
It invokes stop/start through TRE and verifies the VM power states. It changes the overview to exercise a same-version Terraform upgrade and checks that the VM identity remains stable.
The test records the existing firewall as reused. Smoke completes before the bundle job starts.

The job sets `CYCLECLOUD_VALIDATION_DEADLINE` before container setup. The test reserves 120 minutes for cleanup within its 270-minute deadline.
It owns an accepted service before polling. Cleanup waits for terminal operations, verifies ownership and then uses TRE deletion.
It verifies removal of the VM, disk, NIC, storage, blob private endpoint, DNS zone and captured identity's roles. It also checks that the original firewall rules are restored.
Failed cleanup fails the test. Core Key Vault credentials can remain soft-deleted. The test does not retrieve or purge them.

This case does not configure the CycleCloud application or create an HPC cluster. Browser access, application TLS trust, private DNS reachability and prior-release upgrades remain unproven.
The existing bundle grants subscription Contributor to its VM and permits SharedSubnet access to ARM and GitHub. It does not disable the storage public endpoint.
A private endpoint and a successful server lifecycle do not prove workspace isolation or storage access restrictions.
