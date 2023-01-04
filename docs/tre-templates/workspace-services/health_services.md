# Azure Health Data Services Workspace Service

See [Azure Health Data Services Documentation](https://learn.microsoft.com/en-us/azure/healthcare-apis/healthcare-apis-overview).

## Prerequisites

- [A base workspace deployed](https://microsoft.github.io/AzureTRE/tre-templates/workspaces/base/)

## Azure Healthcare Workspace

Each Azure Health Data Services workspace service creates a [Healthcare Workspace](https://learn.microsoft.com/en-us/azure/healthcare-apis/workspace-overview).
In addition, when creating this workspace service you can choose to deploy [FHIR](https://learn.microsoft.com/en-us/azure/healthcare-apis/fhir/) and [DICOM](https://learn.microsoft.com/en-us/azure/healthcare-apis/dicom/) instances within the newly created healthcare workspace.

![Healthcare Service](images/hs_details.png)

## Authentication

Learn more about authentication and application roles in [this doc](https://learn.microsoft.com/en-us/azure/healthcare-apis/authentication-authorization). Make sure to assign your users/apps with the required role and follow the guidelines to retrieve a token.

Notice: If you are using a separate tenant for authentication follow [this documentation](https://learn.microsoft.com/en-us/azure/healthcare-apis/azure-api-for-fhir/configure-local-rbac) to assign users/apps to your FHIR instance.

