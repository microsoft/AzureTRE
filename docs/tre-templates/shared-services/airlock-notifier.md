# Airlock Notifications Shared Service

This shared service connects to the Airlock's notification event grid and send emails to the researchers/ws owners upon Airlock requests changes.

## Development and modification

This service was built with extensibility and modification in mind, since each organization might have different messaging platform and preferences.

From that reason, and for low-code development, Airlock notification service (or Airlock Notifier) is defined in an [Azure Logic App](https://docs.microsoft.com/en-us/azure/logic-apps/) workflow.

Editing the workflow can be done through the Azure Portal, or with the [Azure Logic Apps (Standard) Visual Studio Code extension](https://docs.microsoft.com/en-us/azure/logic-apps/create-single-tenant-workflows-visual-studio-code).
In this repository, you will find that as the default, the email is sent using the [Logic App SMTP connector](https://docs.microsoft.com/en-us/azure/connectors/connectors-create-api-smtp).
Since the connector is 'Managed', your environment or firewall must allow access for the [outbound IP addresses](https://docs.microsoft.com/en-us/connectors/common/outbound-ip-addresses) used by these connectors in your datacenter region.
In the future, the SMTP connection should transition into a ['Built-in connector'](https://docs.microsoft.com/en-us/azure/connectors/apis-list#connector-categories), thus running in the same cluster as the Azure Logic Apps host runtime, and using virtual network (VNet) integration capabilities to access resources over a private network.

As an alternative to the SMTP connector, you can modify the Logic app to use other email and messaging platforms as connectors, like [Office 365](https://docs.microsoft.com/en-us/azure/connectors/connectors-create-api-office365-outlook),
[Outlook.com](https://docs.microsoft.com/en-us/azure/connectors/connectors-create-api-outlook), [MailChimp](https://docs.microsoft.com/en-us/connectors/mailchimp/), [Mandrill](https://docs.microsoft.com/en-us/connectors/mandrill/).

## Storage and network

The Logic App keeps its runtime state and its files in the core storage account `stg<tre_id>`. This account accepts traffic only through its private endpoints and from trusted Azure services. The Logic App uses virtual network integration and the app setting `WEBSITE_CONTENTOVERVNET` to reach the blob, file, queue and table endpoints of the account.

Terraform creates the content share `airlock-notifier-content-<tre_id>` before the Logic App. Before version 1.0.15, the platform created the content share `airlock-notifier-app-<tre_id>-content` outside Terraform. The upgrade to 1.0.15 deploys the workflow to the new share. After the upgrade, you can delete the earlier share.

If you upgrade the core to version 0.18.16 or later, upgrade the notifier to 1.0.15 directly after the core. Azure mounts the content share of earlier notifier versions over the public network, and the storage account no longer accepts this traffic. A running notifier can continue to work, but a restart or a configuration change of its Logic App can fail until the upgrade.
