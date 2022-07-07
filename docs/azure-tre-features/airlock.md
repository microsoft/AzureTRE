# Airlock

In a Trusted Research Environment (TRE) the workspaces represent a security boundary that enables researchers to access data, execute analysis, apply algorithms and collect reports. The airlock capability brings the only mechanisme that allows users to `import` or `export` data and tools in a secure fashion with a manual approval.
This constitutes the mechanism focused in preventing malware inside TRE and/or TRE workspaces and preventing data exfiltration, while allowing researchers to execute their tasks.
The airlock feature brings several actions: ingress/egress Mechanism; Data movement; Security gates; Approval mechanism and Notifications. As part of TRE's Safe settings all activity must be tracked for auditiing purpose.

The Airlock feature aims to address these goals:
* Prevent unauthorised data export (or import).
* Provide a process to allow approved data into the security boundary of a TRE Workspace.
* TRE provides functionality to track requests and decisions, supporting cycle of revision, approval or rejection.
* Data being imported with an airlock import process must be automatically scanned for security purpose.
* Data bein exported or imported must ne manually reviewed bu the Workspace Owner.
* Notify the involved users of the process progress and/or required actions
* All airlock processes are audited and tracked

Typically in a TRE, the Airlock feature would be used to allow a researcher to export patient identifiers for an exact cohort without the underlying data ever being exposed. Through the airlock, data to be exported is restricted by a manual review ensuring that no data is exfiltered from TRE.

The Airlock feature will create events on every miningful step of the processes. This will enable increased flexibility by allowing an organization to extend several underlying mechanisms.

## Ingress/Egress Mechanism

The Ingress/Egress Mechanism allows a TRE user to start `import` or `export` process to a given workspace. The mechanism provides a set of milestones that must be reached in order to execute a process end to end. This milestones end up to be states:

a. **Draft**: An import/export process has been created but has not yet started. The TRE User/Researcher has now access to a storage location and he must identify the data to be processed. At this point the airlock import/export processes allow a single file to be processed. However a compressed file may be used (zip).
b. **Submitted**: The request was submitted by the ressearcher (not yet processed).
c. **In-Review**: The request was submitted is in review.
d. **Approval In-progress**: The import/export process has been approved, however data movement is still ongoing.
e. **Approved**: The import/export process has been approved. At this state, data has been securely verified and manually reviewed. The data is now in its final location. For an import process the data is now available in the TRE workspace. It can be accessed by the requestor from within the workspace.
f. **Rejection In-progress**: The import/export process has been rejected, however data movement is still ongoing.
g. **Rejected**: The import/export process has been rejected. The data in the process was rejected manually by the Airlock Manager.
h. **Cancelled**: The import/export process was manually cancelled by the requestor TRE user, a Workspace owner or a TRE administrator. The cancelation is only allowed when the request is not actively changing (i.e. **Draft** or **In-Review** state).
i. **Blocking In-progress**: The import/export process has been blocked, however data movement is still ongoing.
j. **Blocked By Scan**: The import/export process has been blocked. The security analysis found issues in the submitted data, and consequently quarantined the data.

When an airlock process is created the state is **Draft** and thre request infrastructure will get created providing a single container to centralize data in the request. Once the processThe user will get a link for this container inside the storage account (URL + SAS token) that he can use to upload the desired data to be processed (import or export).
This storage location is external for import (`stalimex`) or internal for export (`stalexint`), however only accessible to the requestor (ex: a TRE user/researcher).
The user will be able to upload a file to the provided storage location, using any tool of their preference: [Azure Storage Explorer](https://azure.microsoft.com/en-us/features/storage-explorer/) or [AzCopy](https://docs.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-v10) which is a command line.

The user Submits the request (TRE API call) starting the data movement (to the `stalimip` - import in-progress or `stalexip` - export in-progress). The airlock request is now in state **Submitted**.
If enabled, the Security Scanning is started. In case security flaws are found, the request state becomes **Blocking In-progress** while the data is moved to storage rejected (either rejected import `stalimrej` or rejected export `stalexrej`). In this case, the request is finalized with the state **Blocked By Scan**.
If the Security Scanning does not identify security flaws, the request state becomes **In-Review**. Simultaneously a  notification is sent to the Airlock Manager user providing the access to data (SAS token + URL with READ permission).

> The Security Scanning can be disabled, chaging the request state from **Submitted** straight to **In-Review**.

The Airlock Manager will manually review the data using the tools of their choice available in the TRE workspace. Once review is completed, the Airlock Manager will have to *Approve* or *Reject* the airlock proces, though a TRE API call.
At this point, the request will change state to either **Approval In-progress** or **Rejection In-progress**, while the data movement occurs moving afterwards to **Approved** or **Rejected** accordingly. The data will now be in the final storage destination: `stalexapp` - external approved export or `stalimapp` - internal approved import.
With this state change a notification will be triggered to the requestor including the location for the processed data in the form of an URL + SAS token.

## Data movement

For any airlock process there is data movement either **into** a TRE workspace (in import process) or **from** a TRE workspace (in export process). Being the TRE a Workspace boundary, there are networking configurations designed to achieve this goal. The data movement will guarantee that the data is automatically verified for securty flaws and manually reviewed, before placing data inside the TRE Workspace.
Also, the process guarantees that data is not tampered with through out the process.

In an import process, data will transition from more public locations (yet confined to the requestor) to TRE workspace storage, after guaranteeding security automatically and by manual review.

In an export process data will transition from internal locations (available to the requetor) to public locations in the TRE, after going through a manual review.

Considering that the Airlock requests may require large data movements, the operations can have longer durations, hence becoming the operations asynchronous. This is why states like **Approval In-progress**, **Rejection In-progress** or **Blocking In-progress** will be set while there are data movement operations.

> The data movement mechanism is data-driven, allowing an organization to extend how request data transitions between

## Security Scan

The identified data in a airlock proces, will be submited to a security scan. If the security scan identifies issues the data is quarantine, and a report is added to the process metadata. Both the requestor and Workspace Owner are notified. For successful security scan, the data will remain in state **In-progress**, and accessible to the Workspace Owner.

> * The Security scan will be optional, behind a feature flag, enabled by script
> * The outcome of security scan will be either the in-progress (`stalexip`) storage or rejected (`stalexrej`)
> * An airlock process will guarantee that the content being imported/exported is secure. It is envisioned that a set of **security gates** are identified to be executed successfully for a process to be approve.

## Approval mechanism

The approval mechanism, is bundled with any airlock process, providing a specific way to `approve` or `reject` the data. This mechanism will allow the Airlock Managers to explicitly approve/reject the process, after having acess to the data. The Airlock Manager users will be able to execute a manual review on the data using the tools available to him in a reviewal TRE Workspace.
Once this manual review is executed, Airlock Managers can proactivelly approve or reject the airlock request.

The only responsability of the Approval mechanism is to support a cycle of revision, approval or rejection, while tracking the decision.

This mechanism will provice access to the data in the airlock process, and will be able to use a VM in TRE workspace. The data review will be the Airlock Manager responsability

> * It is envisioned that this mechanism to be more flexible and extensible.
> * The `Airlock Manager` is a role defined at workspace instance level and assigned to identities. Initially the `Owner` role will be used.

## Notifications

Throughout the airlock process, the notification mechanism will notify the relevant people to the process. Both the requestor (TRE User/Researcher) and the Workspace Owner will be notified by email, of the relevant process events.

Whenever the airlock process changes to a state of **Draft**, **Submitted**, **Approved**, **Rejected** , **Blocked By Scan** or **Cancelled**, the process requestor gets notified.
When the state changes to `In-progress` the Workspace Onwer (Airlock Manager) gets notified.

> * The Notification mechanism is also data-driven, allowing an organization to extend the notifications behavior. The mechanism is exemplified with a Logic App determining the notifications logic.
> * Notifications will work with All TRE users being AAD users (guests or not), with email defined – if not, notifications will not be sent.

### Architecture

The Airlock feature is supported by infrastructure at the TRE and workspace level, containing a set of storage accounts. Each Airlock request, will provision and use unique storage containers with the request id in it's name.

TRE:
* `stalimex` - storage (st) airlock (al) import (im) external (ex)
* `stalimip` - storage (st) airlock (al) import (im) in-progress (ip)
* `stalimrej` - storage (st) airlock (al) import (im) rejected (rej)
* `stalimblocked` - storage (st) airlock (al) import (ex) approved (app)
* `stalexapp` - storage (st) airlock (al) export (ex) approved (app)

Workspace
* `stalimapp` - workspace storage (st) airlock (al) import (im) approved (app)
* `stalexint` - workspace storage (st) airlock (al) export (ex) internal (int)
* `stalexip` - workspace storage (st) airlock (al) export (ex) in-progress (ip)
* `stalexrej` - workspace storage (st) airlock (al) export (ex) rejected (rej)
* `stalexblocked` - workspace storage (st) airlock (al) export (ex) rejected (rej)

> * The external storage accounts (`stalimex`, `stalexapp`), are not bound to any vnet and accessible (with SAS token) via internet.
> * The internal storage account (`stalexint`) is bound to the workspace vnet, so ONLY TRE Users/Researchers on that workspace can access it
> * The (export) in-progress storage account (`stalexip`) is bound to the workspace vnet
> * The (export) blocked storage account (`stalexblocked`) is bound to the workspace vnet
> * The (export) rejected storage account (`stalexrej`) is bound to the TRE CORE vnet
> * The (import) in-progress storage account (`stalimip`) is bound to the TRE CORE vnet
> * The (import) blocked storage account (`stalimblocked`) is bound to the TRE CORE vnet
> * The (import) rejected storage account (`stalimrej`) is bound to the TRE CORE vnet
> * The (import) approved storage account (`stalimapp`) is bound to the workspace vnet

In the TRE Core, the TRE API will provide the airlock API endpoints allowing to advance the process. The TRE API will expose the following methods:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/workspaces/{workspace_id}/requests` | Create an Airlock request (in **Draft**) |
| `POST` | `/api/workspaces/{workspace_id}/requests/{airlock_request_id}/link` | Get the url and token to acccess Airlock Request | `POST` | `/api/workspaces/{workspace_id}/requests/{airlock_request_id}/submit` | Submits an Airlock request |
| `POST` | `/api/workspaces/{workspace_id}/requests/{airlock_request_id}/reviews` | Reviews an Airlock request |
| `POST` | `/api/workspaces/{workspace_id}/requests/{airlock_request_id}/cancel` | Cancels an Airlock request |
container |

Also in the airlock feature we have the **Airlock Processor** which will handle the events that are created throughout the process, signalling state changes from blobs created, status changed or security scans finalized.
