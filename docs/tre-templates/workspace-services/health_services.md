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
Azure fails an endpoint to a healthcare workspace without a FHIR or DICOM service. So Terraform creates the endpoint after FHIR and DICOM, and each Health service must deploy FHIR, DICOM or both.
If an install or an update has neither FHIR nor DICOM, Terraform stops before it changes a resource, with the message "Deploy FHIR, DICOM or both".
This also applies to an upgrade of an earlier Health service without FHIR and DICOM. Turn on FHIR or DICOM in the same request, or delete the service.
The form of the TRE UI turns on FHIR by default. A request through the API without `deploy_fhir` keeps the bundle default `false`.
Azure writes the private DNS records of a zone when the DNS zone group of this endpoint gets that zone.
The DNS zone group always has the zone for the workspace and FHIR. It has the DICOM zone only when the service has DICOM.
If an update adds DICOM, Terraform adds the DICOM zone to the group, and Azure writes the DICOM record. The endpoint stays.
The FHIR record is in the same zone as the workspace record. So if an update adds or removes FHIR, Terraform deletes the group before the FHIR change and creates it again after the change. Azure then writes the records again.
Private access to the healthcare workspace and DICOM stops until the new group exists. For an update that adds FHIR, this time includes the FHIR create, which took 9 to 12 minutes in tests.
If the FHIR change fails, the new group does not exist, and private access stays stopped. To repair the service, run the update again.
Azure links a new service to the endpoint some minutes after Terraform creates the service.
During this time, Azure refuses a change to the DNS zone group with HTTP 409, and Terraform tries again.

Before version 0.3.9, the endpoint resource created the DNS zone group, and the group did not change when an update added a service.
If you added DICOM to an existing service before this version, the DICOM host can resolve to a public address.
An upgrade to version 0.3.9 deletes the old DNS zone group and creates a new one, so Azure writes the missing record.
Terraform deletes the old group after the changes to FHIR and DICOM, directly before it creates the new group.
Until the upgrade creates the new group, the private DNS records do not exist, and private access to the services stops.
Do not delete the private endpoint to repair the service.

The DICOM service has public network access turned off.
Before version 0.3.9, Terraform created the DICOM service with public network access on.
An upgrade to version 0.3.9 turns it off.

The private endpoint on the healthcare workspace blocks public traffic to FHIR and DICOM.
A request from outside the workspace network gets HTTP 403.
The FHIR service reports `publicNetworkAccess` `Enabled`, but Azure does not use this value when the workspace has an approved private endpoint.
Azure also keeps this value when a request sets it to `Disabled`.

## Authentication

Learn more about authentication and application roles in [this doc](https://learn.microsoft.com/en-us/azure/healthcare-apis/authentication-authorization). Make sure to assign your users/apps with the required role and follow the guidelines to retrieve a token.

Notice: If you are using a separate tenant for authentication follow [this documentation](https://learn.microsoft.com/en-us/azure/healthcare-apis/azure-api-for-fhir/configure-local-rbac) to assign users/apps to your FHIR instance.
