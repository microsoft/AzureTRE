# Configuring Airlock Review feature

Airlock Review feature allows to setup a process for manually reviewing Airlock requests. When using this feature, Airlock Manager (a role with privileges of reviewing Airlock requests) is able to create Review User Resource (VM) and use it to review the data from.

For information on Airlock feature, please refer to the [overview page](../azure-tre-overview/airlock.md).

For documentation on how to review an Airlock request, please refer to the [user guide](../using-tre/tre-for-research/review-airlock-request.md).

## Pre-requisites

The feature is configured on a per Research Workspace basis. Different Research Workspaces need to be configured separately, although a single Airlock Import Workspace can be reused for all of them.


To configure the feature, the following prerequisites need to be fulfilled:

1. A deployed Research workspace. Note that if is a base workspace, the template of the workspace must be of version 0.5.0 or later and airlock must be enabled in it.

[![Enable airlock in workspace](../assets/enable-airlock.png)](../assets/enable-airlock.png)


For import:

1. [Airlock Import Workspace](../tre-templates/workspaces/airlock-import-review.md) need to be deployed (once per TRE). To make this template available in your TRE run the following make command:
`make workspace_bundle BUNDLE=airlock-import-review`
Note: TRE Admin permissions are required to register the template
Having the template in place. Deploy a new workspace that will be used for Airlock import reviews.

1. [Guacamole Workspace Service](../tre-templates/workspace-services/guacamole.md) need to be deployed in Airlock Import Workspace from the previous step.

1. [Template for import review VM](../tre-templates/user-resources/import-reviewvm.md) needs to be installed in the TRE, or a custom template if used. To add the existing review VM template to your TRE run the following make command:
`make user_resource_bundle WORKSPACE_SERVICE=guacamole BUNDLE=guacamole-azure-import-reviewvm`
Note: TRE Admin permissions are required to register the template

For export:

1. [Guacamole Workspace Service](../tre-templates/workspace-services/guacamole.md) need to be deployed in Research Workspace.

1. [Template for export review VM](../tre-templates/user-resources/export-reviewvm.md) needs to be installed in the TRE, or a custom template if used. To add the existing review VM template to your TRE run the following make command:
`make user_resource_bundle WORKSPACE_SERVICE=guacamole BUNDLE=guacamole-azure-export-reviewvm`
Note: TRE Admin permissions are required to register the template



## Configuring Airlock VM for Research Workspace

To allow the Airlock Import Review feature in your workspace navigate to Research Workspace in the UI, and click "Update". You will see a check box "Configure Review VMs".

[![Configure Review VM](../assets/configure-review-vm.png)](../assets/configure-review-vm.png)

You then will be able to input the values as follows:

1. For `Import Review Workspace ID`, use the GUID of the Airlock Import Review workspace from step 1.
1. For `Import Review Workspace Service ID`, use the GUID of the Workspace Service from step 2.
1. For `Import Review VM User Resource Template Name`, unless you have built a custom template for this, you should use `tre-service-guacamole-import-reviewvm` which is the name of the standard template used for Import Reviews from step 3.
1. For `Export Review Workspace Service ID`, use the GUID of the Workspace Service deployed into the Research Workspace from step 4.
1. For `Export Review Vm User Resource Template Name`, unless you have built a custom template for this, you should use `tre-service-guacamole-export-reviewvm` which is the name of the standard template used for Import Reviews from step 5.

Once you're done, click Submit.

Verify that the configuration is working by creating Review VMs for existing import export and export requests (configuration is not verified on update).

For troubleshooting guidance please review [the airlock troubleshooting FAQ](../troubleshooting-faq/airlock-troubleshooting.md)
