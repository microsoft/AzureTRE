# Microsoft Entra ID Tenant Choices

## Dedicated Tenant for TRE

We recommend that you have a dedicated Tenant for your TRE rather than using your corporate tenant. This is because TRE is able to automate some of the AD Tenant Admin tasks for you. In order to do this, there is an Admin User that has the ability to create AD Applications. This would not be normal for a Corporate Tenant.

Users from your corporate tenant can be guested into this new TRE tenant.

[![TRE Tenant](../../assets/tre-tenant.png)](../../assets/tre-tenant.png)

## Corporate Tenant

It is possible to use your corporate tenant for TRE. This does have the advantage of only managing a single tenant, but your Microsoft Entra ID Tenant Admin must be aware of what TRE brings to your organization and must be prepared to carry out some admin tasks, like creating an Microsoft Entra ID Application every time a new Workspace is created.

[![TRE Tenant](../../assets/corp-tenant.png)](../../assets/corp-tenant.png)

## Create Dedicated Microsoft Entra ID Tenant

Follow [this guide](https://learn.microsoft.com/en-us/entra/fundamentals/create-new-tenant) to create new dedicated tenant.

## Next steps

* [Setup Auth configuration](./setup-auth-entities.md)
