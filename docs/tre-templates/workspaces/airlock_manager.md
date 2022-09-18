# Airlock Manager workspace

**NOTE**: This feature is still in active development. More documentation will be added as the development progresses.

Airlock Manager workspace is used as part of Review workflow for [Airlock](../../azure-tre-overview/airlock.md).
It allows to review Airlock Data Import requests from, by providing a workspace to spin up VMs in that then can access the in-progress storage account.

The workspace is built upon the base workspace template. It adds a private endpoint to connect to import in-progress storage account, adds corresponding roles, and disables shared storage for VMs.
