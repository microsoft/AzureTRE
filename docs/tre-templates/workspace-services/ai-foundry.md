# Azure AI Foundry model service

This workspace service deploys one Foundry account, one default project and one approved OpenAI chat model.
By default, users access the model from the workspace network with Microsoft Entra ID authentication.
Public network access and API key authentication are independent, optional settings.

The supported scope is inference through the OpenAI chat completions API.
The Foundry browser playground, agents, tools, knowledge search, file uploads and external connections are outside the supported scope.
This support limit is not a guarantee that RBAC denies every other API operation. See [Role selection rationale](#role-selection-rationale).
The service does not receive access to shared workspace storage.

## Prerequisites

- Deploy core `0.17.0` or later before creating or upgrading the base workspace.
- Use base workspace `2.11.0` or later with `auth_type=Automatic` and `create_aad_groups=true`.
- Add users to the appropriate parent workspace group. A TRE application role alone does not grant Azure model access.
- Use Azure public cloud and a region that supports the template's model and Standard deployment tier.
- Check model quota before installation. The default capacity is 10 units of 1,000 tokens per minute.
- The deployment identity needs permission to manage role assignments on the Foundry account and, when keys are enabled, its Key Vault secret.
- Before using sensitive data, review the [hosted-tool controls](#hosted-tool-controls) and verify every required runtime restriction.

Fresh installations do not require custom role definition permissions. Upgrades from the earlier custom-role version require cleanup permissions described below.

The service creates a private endpoint for Cognitive Services, OpenAI and Foundry account endpoints.
The core and base workspace changes supply the Foundry private DNS zone and its VNet links.

## Workspace subscription

The TRE API supplies `workspace_subscription_id` from the parent workspace.
An empty value uses the core subscription.
The account, project, model, private endpoint, Key Vault secret and role assignments use the workspace subscription.
Private DNS zone lookups use the core subscription. Account deletion and purge target the workspace subscription.
For local Porter commands, set `WORKSPACE_SUBSCRIPTION_ID` to the workspace subscription, or leave it empty to use core.
The deployment identity needs access to workspace resources and the core private DNS zones.

## Access settings

| Setting | Default | Effect when enabled |
| --- | --- | --- |
| `is_exposed_externally` | `false` | Allow authenticated requests from public networks as well as the private endpoint. |
| `local_auth_enabled` | `false` | Accept API keys alongside Entra tokens and store the key in the workspace Key Vault. |

Both settings can be changed through TRE after installation.
API keys work in private mode. Public access does not enable keys or anonymous access.
Disabling API key authentication leaves Entra authentication available.

## Create and use the service

1. Sign in to TRE as a WorkspaceOwner.
2. Open the workspace's **Workspace services** page.
3. Create an **Azure AI Foundry workspace service**.
4. Select the approved model, capacity and access settings.
5. Wait for the deployment to complete.
6. Read `openai_endpoint` and `openai_model_deployment` from the service properties returned by the TRE API.
7. Use a workspace desktop with an account in the workspace Owners or Researchers group.
8. Obtain an Entra token for `https://cognitiveservices.azure.com/.default` using the TRE tenant.
9. Call the endpoint's chat completions API with that token and deployment name.

Use a token-aware SDK or client. Keep tokens out of command output, source code and logs.
The service does not expose a browser Connect link. Subscription discovery through Azure Resource Manager is outside the supported client flow.

Initial account provisioning includes a ten-minute readiness wait.
The model catalogue read and model deployment depend on this wait.
Allow time for Azure to apply new group memberships and role assignments.
If access fails, check the failed operation and effective identity permissions before changing a role.

### Use an API key

API keys bypass per-user Entra role checks.
Enable this option only when the workspace permits shared credentials with broader access to this account's APIs.

1. Select **Enable API key authentication** in the service settings.
2. Wait for the deployment or update to complete.
3. Read `openai_api_key_secret_id` from the service properties returned by the TRE API.
4. Retrieve that secret with an Entra identity in the workspace Owners or Researchers group.
5. Supply the secret value to the client's API key setting or the HTTP `api-key` header.

Retrieve the secret from a network that can reach the workspace Key Vault.
Enabling public Foundry access does not change Key Vault networking.
The secret URI is versionless so clients can retrieve the latest stored key.
The service outputs contain the URI, never the key value. Terraform state contains the key and must remain access-controlled.
Keep the key out of source code, command output and logs.

## Permissions

The service assigns the built-in `Cognitive Services OpenAI User` role to the parent workspace's Owners and Researchers groups.
Assignments apply to this Foundry account only, not the workspace resource group or subscription.
The role permits OpenAI inference and read access. TRE service management still requires the existing WorkspaceOwner role.

| Identity | Model access through Entra | TRE service management | Direct Azure security administration |
| --- | --- | --- | --- |
| Workspace Researcher | Yes | No | No |
| WorkspaceOwner in the Owners group | Yes | Yes | No |
| TREAdmin without workspace membership | No | Existing TRE role rules apply | No additional permission |
| Airlock Manager only | No | No | No |
| Non-member | No | No | No |

The inference role grants no account-key retrieval, model deployment changes, role assignment changes, network changes or lock changes.
When keys are enabled, the service separately grants both workspace groups `Key Vault Secrets User` on this service's secret only.
This grant does not expose other workspace secrets or permit key rotation through Azure management APIs.
Inherited Azure permissions remain effective. Use separate, unprivileged accounts to test these boundaries.

API key requests do not use these Entra role assignments.
Anyone holding a valid key can use the account's key-enabled APIs from an allowed network, regardless of their workspace group membership.
Removing a user from a workspace group does not invalidate a key they already hold.
Disable key authentication to block key requests. Rotate shared keys when revoking a key holder's access.
After rotating the account's primary key, upgrade the service to refresh the Key Vault secret, then refresh clients' cached keys.
Microsoft documents these differences in its [Foundry authentication comparison](https://learn.microsoft.com/en-us/azure/foundry/concepts/authentication-authorization-foundry).

### Role selection rationale

We choose `Cognitive Services OpenAI User` as the closest built-in fit for the supported OpenAI inference flow.
Using a Microsoft-maintained role avoids creating and maintaining a custom role definition for each service.
Both workspace groups receive the same model permissions. Owners manage infrastructure through TRE rather than direct Azure administration.

Microsoft's [OpenAI permissions guide](https://learn.microsoft.com/en-us/azure/foundry-classic/openai/how-to/role-based-access-control#cognitive-services-openai-user) confirms Entra inference access without account-key retrieval, deployment management or fine-tuning.
This separates model use from infrastructure management without selecting a contributor role.

The accepted trade-off is broader data access than the previous chat-only custom role.
The [built-in definition](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-openai-user) also includes embeddings, audio, image/video generation, Assistants and Responses permissions where those APIs are available.
The template does not advertise or validate those features, but it does not enforce a chat-only RBAC boundary.
Disabling keys does not remove these Entra permissions. Private networking does not narrow the role's permitted operations.
Microsoft can update built-in permissions. Recheck the definition when reviewing a release.

We do not assign [Cognitive Services OpenAI Contributor](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-openai-contributor), which adds deployment management and broader OpenAI access.
We do not assign [Foundry User](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/ai-machine-learning#foundry-user), which includes account-key retrieval and broad Cognitive Services data permissions.
If maintainers identify a supported operation that needs more access, record the operation and missing permission before reviewing a higher-privilege role.
Any change must retain the narrowest applicable scope and update the tests and documented permission boundary. There is no automatic role escalation.

Neither a resource lock nor a private endpoint replaces authorisation checks.
[Resource locks apply to control-plane operations](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/lock-resources#understand-scope-of-locks), not model requests.

## Network access

The service adds one HTTPS application rule for `login.microsoftonline.com`, scoped to the parent workspace address space.
Workspace model requests use the private endpoint in both network modes.
When `is_exposed_externally=true`, the account also accepts authenticated requests from all public networks.
When it is `false`, public network access is disabled and the account's network ACL defaults to Deny.
The template adds no portal, Azure management, package or image-registry destinations.
The account's [outbound restriction](https://learn.microsoft.com/en-us/azure/ai-services/cognitive-services-data-loss-prevention) remains enabled for every `allowed_fqdns` value.
The default list contains only `deny-all.invalid`.
The [reserved `.invalid` domain](https://www.rfc-editor.org/rfc/rfc6761#section-6.4) does not resolve publicly. This sentinel allows no usable public destination.
Version `0.4.7` uses this non-empty list because live validation found that an empty list did not enforce the required restriction.
External image URLs and other service-initiated URL fetches are outside the supported scope. Verify their rejection in the deployment.

### Allowed outbound FQDNs

Version `0.5.0` exposes `allowed_fqdns` through the TRE service settings and Porter.
The TRE property is an updateable array of exact hostnames, defaulting to `["deny-all.invalid"]`.
It controls Foundry's service-initiated requests, not the workspace firewall or client network access.
Adding hosts permits outbound access to them and can allow data to leave Foundry. Review each destination before adding it.
Allowing a host does not add its tools or API features to this template's supported scope.

**Warning:** removing the last hostname, including the sole `deny-all.invalid` entry, leaves `[]` and removes the workaround.
In live tests on 25 September 2026, an empty list allowed external image requests, MCP metadata retrieval and MCP tool invocation.
The outbound restriction flag remained enabled. Do not rely on an empty list to block outbound access while this behaviour persists.
The template passes an explicit empty list to Azure unchanged. It does not silently restore the sentinel.

| Value | Effect |
| --- | --- |
| `["deny-all.invalid"]` | Default. The tested external image and MCP requests were explicitly rejected. |
| `["deny-all.invalid", "learn.microsoft.com"]` | Permits the named real host. The sentinel does not override another allowed entry. |
| `["learn.microsoft.com"]` | Removes the sentinel but keeps a non-empty allowlist permitting the named host. |
| `[]` | Removes the workaround. The tested external requests were accepted despite the restriction flag. |

Use the following TRE service property to restore the default:

```json
{
  "allowed_fqdns": ["deny-all.invalid"]
}
```

Use hostnames only, without a scheme, port, path, wildcard or blank entry. Duplicate entries are rejected.
Microsoft [documents a maximum of 1,000 entries and up to 15 minutes for propagation](https://learn.microsoft.com/en-us/azure/ai-services/cognitive-services-data-loss-prevention#enabling-data-loss-prevention).
Wait for propagation, then validate the required API paths. Configured values alone do not prove enforcement.

For direct Porter use, the parameter is a base64-encoded JSON array, following TRE's complex-parameter convention.
Its default is `WyJkZW55LWFsbC5pbnZhbGlkIl0=`, encoding `["deny-all.invalid"]`.
An explicit empty array is `W10=`. An empty string is invalid and is not the same as an empty array.
The local parameter-set environment variable is `ALLOWED_FQDNS`. The TRE resource processor performs the encoding for API-supplied arrays.
The default applies when no value is supplied or retained from a previous run.
[Porter remembers previous values during upgrades](https://porter.sh/docs/introduction/concepts-and-components/intro-parameters/), so omission does not reset an existing value.
To restore the default, explicitly supply `["deny-all.invalid"]` through TRE, or its base64 encoding through Porter.

### Why the browser playground is excluded

The Foundry portal needs shared Azure management hosts, including `management.azure.com`.
The template's [FQDN firewall rules](https://learn.microsoft.com/en-us/azure/firewall/domain-filtering-overview) match the hostname, not the account or tenant in a request.
A researcher could hold other Azure credentials. Permissions on this Foundry account do not govern those other resources.

[Azure Policy assignments](https://learn.microsoft.com/en-us/azure/governance/policy/overview#assignments) govern their resource scope and its children.
A policy on this TRE cannot govern resources in an unrelated tenant or subscription.
Therefore the MVP does not add this management-host allowance or advertise browser playground support.
A later portal feature requires a separately reviewed network design.
Existing TRE rules from other services remain effective. Validation must check the combined firewall policy, not just this template.

### Optional deployment governance

Microsoft provides [built-in policies](https://learn.microsoft.com/en-us/azure/ai-services/policy-reference) for local authentication, network restrictions and approved model deployments.
The local-authentication policy supports Deny, which can prevent key authentication being enabled by a later resource update.
Terraform disables key authentication by default. An applicable Deny policy can prevent an operator from enabling the optional key setting.
A policy assignment is an additional operator governance decision, not a prerequisite imposed by this service.
An Audit effect reports non-compliance without blocking it. Neither effect replaces runtime RBAC permissions.

### Hosted-tool controls

The built-in inference role permits Responses API requests, including requests that specify hosted tools.
Excluding these tools from the supported client flow does not disable them for direct API callers.
The account's outbound restriction, Bing resource policies and subscription web-search block are separate controls.

#### Bing resource policy

Base workspace `2.12.0` provides an optional [blocked resource types setting](../workspaces/base.md#blocked-azure-resource-types).
Set the following workspace property to deny Bing account creation and updates in that workspace:

```json
{
  "blocked_resource_types": ["Microsoft.Bing/accounts"]
}
```

The list defaults to empty, so the policy is opt-in. It denies all Bing account kinds, not only one grounding tool.
The base workspace owns the enforced Deny assignment. Deleting a Foundry service does not remove it.
It does not apply outside the workspace resource group. Subscription-wide restrictions require an administrator-owned assignment at that scope.

A [Deny policy](https://learn.microsoft.com/en-us/azure/governance/policy/concepts/effect-deny) blocks matching resource creation and updates.
It does not disable existing accounts, remove their keys or block connections to resources outside its scope.
Review existing Bing accounts and Foundry connections separately using Microsoft's [Bing governance guidance](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/bing-tools#manage-grounding-with-bing-search-and-grounding-with-bing-custom-search).
Do not delete shared resources or unregister their provider as part of this service's uninstall.
This resource policy does not replace the Responses web-search block below.

#### Subscription web-search prerequisite

Microsoft provides a [subscription-wide block for web search](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/web-search#manage-web-search-tool).
It applies to every Foundry account in the selected subscription, including accounts unrelated to this TRE.
For deployments that prohibit web search, the subscription administrator must configure and validate this control before sensitive use.
Registration is outside this workspace-service template's lifecycle. Installation does not register it, and uninstall must not unregister it.

After approving the subscription-wide impact, register the block in the **workspace subscription**, which may differ from the core subscription:

```bash
az feature register --namespace Microsoft.CognitiveServices \
  --name OpenAI.BlockedTools.web_search --subscription "<workspace-subscription-id>"
```

Check the registration state:

```bash
az feature show --namespace Microsoft.CognitiveServices \
  --name OpenAI.BlockedTools.web_search --subscription "<workspace-subscription-id>" \
  --query properties.state -o tsv
```

When the state is `Registered`, [refresh provider registration](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/preview-features#register-preview-feature):

```bash
az provider register --namespace Microsoft.CognitiveServices --subscription "<workspace-subscription-id>"
```

Allow propagation, then verify explicit administrative rejection of both `web_search` and `web_search_preview` with a healthy text-only control.
Registration state alone is not runtime evidence. Throttling, unsupported tools and authentication errors are inconclusive.
The automated outbound suite does not validate web-search enforcement.

#### Remote MCP boundary

The [Responses API accepts remote MCP servers](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses#using-remote-mcp-servers) supplied directly in a request.
It does not require the caller to create a persistent Foundry connection first.
A policy denying connection resources therefore does not close this route.
Tool approval and omission of tools are caller-controlled options, not an administrative deny boundary.
The web-search feature registration does not establish an MCP block.

This template does not configure a separate MCP-disable control.
By default, it sets `restrictOutboundNetworkAccess = true` with `allowedFqdnList = ["deny-all.invalid"]`.
Changing [`allowed_fqdns`](#allowed-outbound-fqdns) changes this boundary, including for MCP requests.
Live validation on 25 September 2026 confirmed explicit domain-policy rejection of Microsoft Learn MCP metadata retrieval and tool invocation with this setting.
The checks used `gpt-5.1` version `2025-11-13` in `switzerlandnorth`.
Text and inline-image controls succeeded. An account that explicitly allowed `learn.microsoft.com` imported metadata and completed the same public documentation search.
The empty-list account accepted both MCP operations and the external image request. The regression tests retain ordinary failures for this behaviour.
Keep the sentinel until repeated empty-list checks confirm enforcement in the target deployment.
These results validate the tested API paths, not every tool or outbound channel. Revalidate before approving a deployment that prohibits remote MCP access.

If the outbound restriction does not enforce the required boundary, a hard restriction requires a reviewed alternative.
A chat-only custom role could remove Responses access for its assignees, but it would replace the selected built-in role and require live permission tests.
API keys must remain disabled, and other assignments must not independently grant Responses access.
Alternatively, an enforcing gateway must reject remote MCP requests and prevent callers from bypassing it to reach Foundry directly.
Neither alternative is implemented by this template. We retain the Microsoft-maintained role and avoid custom roles in this change.
Both alternatives change the current access design and require a separate decision.

## Updates and removal

Workspace owners change the approved capacity and access settings through TRE. Model versions are controlled by the template.
Model availability and retirement are checked against Azure's account catalogue during provisioning.
The template does not fall back to a different model or global deployment tier.

Disable and delete the service through TRE to remove its account, project, deployment, private endpoint and role assignments.
Microsoft's built-in role definition remains unchanged.
The service also removes its firewall collection. It retains the workspace, shared storage and other services.
Account deletion includes a purge of the service's soft-deleted account.

Disabling key authentication removes the secret-reader assignments and soft-deletes the API key secret.
The workspace Key Vault retains the deleted secret under its existing retention policy.
Re-enabling keys recovers the secret and updates it with the account's current primary key.
Service deletion also removes the optional secret and its reader assignments without purging the secret.

Version `0.4.2` replaces the model-only service's previous custom inference role with the built-in role.
On upgrade, Terraform replaces its managed assignments and removes its managed custom role definition.
That cleanup requires `Microsoft.Authorization/roleDefinitions/delete` on the old definition's scope in addition to role-assignment permissions.
Review the upgrade plan and allow for an access interruption while Azure applies the replacement assignments.
The new role grants broader data operations, so review the [permission trade-off](#role-selection-rationale) before upgrading an existing deployment.

The unpublished full-feature prototypes are not an upgrade path into this model-only template.
Create a fresh service for validation. Retain prototype data until its owner approves removal.

## Validation before approval

### Automated checks

| Check | When it runs | Coverage |
| --- | --- | --- |
| Template and CI integration tests | PR Build Validation when Foundry, E2E or related CI files change | Schema validation, private/Entra defaults, outbound allowlist defaults and encoding, Porter settings and secret-reference outputs, bundle registration and pytest selection. |
| Terraform mock tests | The same PR validation | All four access combinations, setting transitions, custom and empty allowlists, private endpoints, built-in role selection and scope, and conditional secret creation. |
| Template smoke tests | Deployment smoke suite | Registered Foundry template and its access-setting defaults. No model deployment. |
| Service lifecycle test | `extended_aad`, including the main-push and nightly suites | Install, repeatable upgrade and removal in a separate Automatic-auth workspace with groups enabled. Private access and Entra authentication remain enabled throughout. |
| Outbound image URL policy checks | Opt-in `foundry_egress` pytest selection against existing accounts | Inline-image controls, explicit domain-policy rejection with empty and unrelated allowlists, and successful retrieval from an allowed domain. No deployment. |
| Outbound MCP policy checks | The same suite with `--foundry-mcp-config` | Text controls, public Microsoft Learn tool discovery and one public documentation search, with explicit domain-policy rejection for restricted accounts. No deployment. |
| Workspace resource policy checks | Existing PR Build Validation when Foundry or base workspace files change | Schema and Porter parameter wiring, opt-in defaults, workspace scope, Deny enforcement, setting changes and assignment removal. Mocked, not live policy enforcement. |

Run the template and CI integration checks locally with Python 3.12:

```bash
python -m pip install -r .github/tests/foundry-requirements.txt
python -m unittest discover -s .github/tests -p 'test_foundry_*.py' -v
```

Run the Terraform checks from `templates/workspace_services/ai-foundry/terraform`:

```bash
terraform init -backend=false -input=false
terraform test
```

The lifecycle test deploys a model at capacity 1. It requires the region, quota and deployment permissions listed above.
For a focused deployed test run, use `make test-e2e-custom SELECTOR=foundry` in the configured development environment.
This selects the Foundry template checks and lifecycle test. Outbound inference checks skip unless explicitly configured as described below.

Before the bundle-matrix changes reach `main`, PR comment commands cannot build and register Foundry in a fresh validation environment.
They use workflow definitions from `main`, even when testing PR code.
A maintainer must run `deploy_tre_branch.yml` from a reviewed branch in the main repository with `e2eTestsCustomSelector=foundry`.
See [PR bot commands](../../tre-developers/github-pr-bot-commands.md) for the workflow and secret-access restrictions.
After merge, `/test-extended-aad` also selects the lifecycle test.

### Outbound image URL policy checks

The Terraform mocks assert `outbound_network_access_restricted = true`, the default sentinel `fqdns = ["deny-all.invalid"]`, and explicit custom and empty lists.
Only live model calls can establish whether Azure enforces those settings.
The checks use the existing E2E suite and pytest JUnit reporting. Their offline tests run in the existing PR Build Validation workflow.
The empty-list control below deliberately remains empty so it detects restored enforcement without a test change.

Provide three existing `AIServices` accounts in one subscription, with identical vision-capable OpenAI model names and versions:

| Account label | Outbound restriction | Allowed FQDNs | External image expectation |
| --- | --- | --- | --- |
| `empty` | Enabled | `[]` | Explicit domain-policy rejection |
| `unrelated` | Enabled | `["example.com"]` | Explicit domain-policy rejection |
| `allowed` | Enabled | `["raw.githubusercontent.com"]` | Successful image processing |

The accounts can reside in different resource groups and use public or private endpoints.
The runner must reach every endpoint and use an Azure CLI identity with account/deployment read access and model inference permission.
The test makes six billable inference calls. It creates, updates and deletes no Azure resources.
Use dedicated control accounts. Do not change a production account's policy to provide a positive control.

1. Wait at least 15 minutes after the accounts' last modification.
2. Save the following JSON outside the checkout, replacing the placeholders:

```json
{
  "subscription_id": "<subscription-id>",
  "tenant_id": "<tenant-id>",
  "model_name": "gpt-5.1",
  "model_version": "2025-11-13",
  "accounts": {
    "empty": {"id": "<empty-account-resource-id>", "deployment": "<deployment-name>"},
    "unrelated": {"id": "<unrelated-account-resource-id>", "deployment": "<deployment-name>"},
    "allowed": {"id": "<allowed-account-resource-id>", "deployment": "<deployment-name>"}
  }
}
```

3. Sign in with Azure CLI to the selected tenant and subscription.
4. Run only the outbound tests from the repository root:

```bash
PYTHONPATH=.:e2e_tests python -m pytest e2e_tests/test_foundry_egress.py -m foundry_egress -n 0 \
  --foundry-egress-config /tmp/foundry-egress.json --junitxml=/tmp/foundry-egress.xml
```

This command does not invoke the TRE workspace or service deployment fixtures.
Keep pytest worker parallelism disabled so the six cases share one set of probes.
It reads the account and model settings before and after the probes and uses fresh image URLs for each run.
An optional top-level `image_url` can select another public HTTPS PNG. Set the `allowed` account's FQDN list to that hostname.
The URL must not contain credentials or query parameters. Redirects are rejected.
Corporate proxy users must supply a trusted combined CA bundle through `REQUESTS_CA_BUNDLE` or `SSL_CERT_FILE`. TLS verification stays enabled.

Successful processing of an external image outside the configured allowlist is a normal pytest failure.
For both restricted cases, a pass requires explicit domain-policy rejection and healthy controls.
Authentication errors, throttling, inbound firewall rejection, unknown policy errors and changed settings are inconclusive pytest errors, never passing rejections.
Without `--foundry-egress-config`, the six live tests skip. Missing or malformed supplied configuration produces errors.
Six passes establish API enforcement for this run, not proof that no outbound fetch occurred. That requires receiver-side logs.

### Outbound MCP policy checks

Use the same JSON account configuration format as the image URL checks, but supply accounts with these policies:

| Account label | Outbound restriction | Allowed FQDNs |
| --- | --- | --- |
| `empty` | Enabled | `[]` |
| `unrelated` | Enabled | `["deny-all.invalid"]` |
| `allowed` | Enabled | `["raw.githubusercontent.com", "learn.microsoft.com"]` |

Use dedicated test accounts with identical model names and versions, and wait at least 15 minutes after policy changes.
The image and MCP matrices have different allowlists. Use separate control accounts if running both matrices together.
Do not change production policies to create these controls. The runner reads settings before and after the requests and changes no Azure resources.
The nine billable Responses requests use only synthetic prompts and Microsoft's public `https://learn.microsoft.com/api/mcp` endpoint.
Discovery requests set `tool_choice: none`. Invocation requests permit one `microsoft_docs_search` call with a fixed public-documentation query.
The test needs enough model quota for the public tool descriptions and results. Rate limiting makes the affected checks inconclusive.

Run the MCP checks from the repository root:

```bash
PYTHONPATH=.:e2e_tests python -m pytest e2e_tests/test_foundry_mcp.py -m foundry_egress -n 0 \
  --foundry-mcp-config /tmp/foundry-mcp.json --junitxml=/tmp/foundry-mcp.xml
```

Both restricted accounts must reject discovery and invocation with an explicit MCP domain-policy error.
Text-only requests must succeed on all accounts. The allowed account must import tool metadata and complete the public search.
Unexpected acceptance is an ordinary test failure. Authentication failures, throttling and unhealthy positive controls are inconclusive fixture errors.
The empty-list checks remain unchanged in purpose: they must pass through actual enforcement, never through an expected-failure marker.
This validates the named API paths and target, not every possible outbound channel. Receiver-side logs are needed to prove absence of network traffic.

### Runtime access checks

Mock tests and lifecycle output checks do not prove live model access, secret access or network enforcement.
Role-selection assertions check the configured built-in role and assignment scope, not Microsoft's live permission definition.
The automatic lifecycle test does not enable public access or API keys.

Use separate attended identities to verify model use and denied model-management, network and role operations.
With keys disabled, verify that API key requests and service-granted secret access are denied.
With keys enabled, verify secret retrieval by both workspace groups and denial for a non-member without inherited access.
Check API key inference from the workspace network and confirm that other workspace secrets remain inaccessible.
Verify that public requests fail in private mode and succeed with valid credentials in public mode.
Check that a non-member's Entra request fails in both network modes.
Disable and re-enable both settings to verify access changes and secret recovery.
Verify removal of group membership with a fresh session after propagation.
Complete service-only uninstall and reinstall checks while neighbouring resources remain available.
