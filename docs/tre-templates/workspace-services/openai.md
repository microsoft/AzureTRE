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
- `openai_model` - The model to use for the OpenAI deployment `<model name> | <model version>`. The default is `gpt-35-turbo | 0301`.
- Important note: Models are subject to different quota and region availability and the deployment may fail if you don't have the correct quota.
Please review this link on current limits and how to request increases: [Open AI Quotas](https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits)
