# Azure Health Data Services Workspace Service

See [Azure Health Data Services Documentation](https://learn.microsoft.com/en-us/azure/healthcare-apis/healthcare-apis-overview).

## Prerequisites

- [A base workspace deployed](https://microsoft.github.io/AzureTRE/tre-templates/workspaces/base/)

## Azure Healthcare Workspace

Each Azure Health Data Services workspace service creates a [Healthcare Workspace](https://learn.microsoft.com/en-us/azure/healthcare-apis/workspace-overview).
In addition, when creating this workspace service you can choose to deploy [FHIR](https://learn.microsoft.com/en-us/azure/healthcare-apis/fhir/) and [DICOM](https://learn.microsoft.com/en-us/azure/healthcare-apis/dicom/) instances within the newly created healthcare workspace.

![Healthcare Service](images/hs_details.png)

## Install failures before version 0.3.9

Before version 0.3.9, an install can fail after Azure creates the FHIR service.
If Azure reports the FHIR service as `Accepted` after the create, the azurerm provider stops its wait, and Terraform does not save the FHIR service.
After this failure, each update and each delete of the Health service fails.
To repair the service, delete its FHIR service in the Azure portal, and then delete the Health service again.

## Private network access

The service connects the healthcare workspace to the workspace network through one private endpoint.
Azure writes the private DNS records for FHIR and DICOM when it creates this endpoint.
If an update adds or removes FHIR or DICOM, Terraform replaces the endpoint, so that each service gets a private DNS record.
During this replacement, private access to the services stops for some minutes.

Before version 0.3.9, an update did not replace the endpoint.
If you added FHIR or DICOM to an existing service before this version, the new host can resolve to a public address.
To repair the service, delete its private endpoint `pe-hs<suffix>` in Azure, then upgrade the service. Terraform then creates the endpoint again.

## Authentication

Learn more about authentication and application roles in [this doc](https://learn.microsoft.com/en-us/azure/healthcare-apis/authentication-authorization). Make sure to assign your users/apps with the required role and follow the guidelines to retrieve a token.

Notice: If you are using a separate tenant for authentication follow [this documentation](https://learn.microsoft.com/en-us/azure/healthcare-apis/azure-api-for-fhir/configure-local-rbac) to assign users/apps to your FHIR instance.
