# OpenAI Workspace Service

See: [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/overview)

## Prerequisites

- [A base workspace deployed](../workspaces/base.md)

- The OpenAI workspace service container image needs building and pushing:

  `make workspace_service_bundle BUNDLE=openai`

## Authenticating

1. The open AI domain and deployment id can be found from the details tab.
2. When communicating with the API, an "api_key" is required. This can be found in the Key Vault.

## Properties
- `is_exposed_externally` - If `True`, the OpenAI workspace is accessible from outside of the workspace virtual network.
- `openai_model` - The model to use for the OpenAI deployment `<model name> | <model version>`. The default is `gpt-5.1 | 2025-11-13`.
- Important note: Models are subject to different quota and region availability and the deployment may fail if you don't have the correct quota.
Please review this link on current limits and how to request increases: [Open AI Quotas](https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits)


## Model prerequisites

The bundle uses the regional `Standard` deployment type with one capacity unit.
Check availability and quota for the exact model version in the workspace region before deployment.
The older model values remain in the schema for existing resource records. Their presence does not mean Azure can deploy them.
Changing the template default does not change the model value stored on an existing service.
An explicit model change can replace the deployment and needs separate upgrade validation.

The OpenAI bundle currently requires the workspace and core in the same subscription.
Private network access remains the default. The bundle does not add researcher RBAC roles or change key authentication.

See [model availability](https://learn.microsoft.com/en-us/rest/api/aiservices/accountmanagement/models/list?view=rest-aiservices-accountmanagement-2024-10-01)
and [subscription quota](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/quota).

## Independent validation

Select `tre-workspace-service-openai` through the [bundle validation procedure](../../tre-developers/end-to-end-tests.md#validate-one-bundle).
The test checks current model and quota prerequisites, deploys a private service, checks its model and network settings, and uninstalls it.
It confirms removal of the API record and active Azure account.
Private inference, researcher access, model upgrades, secret removal and soft-deleted account purge require separate evidence.
