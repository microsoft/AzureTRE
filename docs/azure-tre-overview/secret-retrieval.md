# Secret retrieval

Resources (workspace services and user resources) can surface secret values — such as VM administrator passwords, storage account keys, or database connection strings — to researchers. Rather than storing secret values in the resource document, resources store the secret in the **workspace Key Vault** and output a Key Vault secret identifier (URI) in a property whose name contains `keyvault_secret_id`. The value is fetched on demand when a user chooses to reveal it and is never persisted in the Configuration Store or returned by list operations. See [Exposing secrets to researchers](../tre-workspace-authors/authoring-workspace-templates.md#exposing-secrets-to-researchers) for the authoring convention.

Key Vault access is performed **on behalf of the signed-in user** using an On-Behalf-Of (OBO) token exchange, so a secret is read as the caller rather than as the core API's own identity. This relies on a per-workspace federated identity credential (FIC) instead of a stored workspace client secret.

The components and trust relationships are:

| Component | Role in the flow |
| --- | --- |
| Core API managed identity | Requests a managed-identity token for the token-exchange audience (`api://AzureADTokenExchange`) to use as the client assertion. It holds **no standing Key Vault permission**. |
| Workspace app registration | Acts as the confidential client for the OBO exchange. A federated identity credential names the core API managed identity as its subject, so the API can authenticate *as* the workspace application without a client secret. |
| Caller's access token | Supplied as the user assertion in the OBO exchange, so the resulting Key Vault data-plane token is scoped to that user. |
| Workspace Key Vault | Holds the secrets. Data-plane RBAC on the vault determines which secrets each user can read. |

The flow when a user reveals a secret is:

1. The user calls the resource's secrets endpoint on the TRE API with their bearer token.
1. The API validates that the property is a secret reference (name contains `keyvault_secret_id`) and that the referenced secret lives in the workspace's own Key Vault.
1. The API's managed identity obtains a token-exchange token and uses it as the client assertion to authenticate as the workspace app registration (via the FIC).
1. The API performs an OBO exchange, presenting the caller's token as the user assertion, to obtain a Key Vault data-plane token scoped to the user.
1. The API reads the secret from the workspace Key Vault with that token and returns the value in the response. The value is not stored.

Because the OBO exchange requires the caller's own token, a caller can only ever retrieve secrets they have themselves been granted read access to on the workspace Key Vault — even though the request is proxied through the core API.

## Compromise and blast radius

The federated identity credential lets the core API managed identity authenticate as the workspace application. If the core API managed identity were compromised, an attacker could impersonate the workspace app registration (the client-assertion half of the exchange). To actually read a secret via OBO they would additionally need a valid user token, captured while proxying a request. The blast radius is bounded by:

- the permissions the workspace application itself holds (so workspace applications should be granted least privilege); and
- the secrets the impersonated user can already read (the FIC grants no direct Key Vault access of its own).

This is a deliberately smaller blast radius than the alternatives of storing a workspace client secret or granting the core API standing `Key Vault Secrets User` access to every workspace vault. The core API managed identity should be protected accordingly.
