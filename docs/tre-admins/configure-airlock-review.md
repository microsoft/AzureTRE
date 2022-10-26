# Configuring Airlock Review feature

Airlock Review feature allows to setup a process for manually reviewing Airlock requests. When using this feature, Airlock Manager (a role with privileges of reviewing Airlock requests) is able to create Review User Resource (VM) and use it to review the data from.

For information on Airlock feature, please refer to the [overview page](../azure-tre-overview/airlock.md).

For documentation on how to review an Airlock request, please refer to the [user guide](../using-tre/tre-for-airlock-reviewer/review-airlock-request.md).

## Pre-requisites

The feature is configured on a per Research Workspace basis. Different Research Workspaces need to be configured separately, although a single Airlock Import Workspace can be reused for all of them.
To configure the feature, the following prerequisites need to be fulfilled:

1. Airlock needs to be enabled on creation of the workspace

1. [Airlock Import Workspace](../tre-templates/workspaces/airlock-import-review.md) need to be deployed (once per TRE)
1. [Guacamole Workspace Service](../tre-templates/workspace-services/guacamole.md) need to be deployed in Airlock Import Workspace from the previous step
1. [Template for import review VM](../tre-templates/user-resources/import-reviewvm.md) needs to be installed in the TRE

1. [Guacamole Workspace Service](../tre-templates/workspace-services/guacamole.md) need to be deployed in Research Workspace
1. [Template for export review VM](../tre-templates/user-resources/export-reviewvm.md) needs to be installed in the TRE

## Configuring Airlock VM for Research Workspace

Research Workspace can only be configured after it has been deployed.

> This document is still a work in progress. This section will be updated once https://github.com/microsoft/AzureTRE/issues/2741 is done

