# Airlock Import Review workspace

Airlock Import Review workspace is used as part of Review workflow for [Airlock](../../azure-tre-overview/airlock.md).
It allows to review Airlock Data Import requests from, by providing a workspace to spin up VMs in that then can access the in-progress storage account.

The workspace is built upon the base workspace template. It adds a private endpoint to connect to Imlort In-Progress storage account, and disables shared storage for VMs.
