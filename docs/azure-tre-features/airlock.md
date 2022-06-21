# Airlock

In a Trusted Research Environment (TRE) the workspaces represent a security boundary that enables researchers to access data, execute analysis, apply algorithms and collect reports. The airlock capability brings the only mechanisme that allows users to `import` or `export` data and tools in a secure fashion with a manual approval.
This constitutes the mechanism focused in preventing malware inside TRE and/or TRE workspaces and preventing data exfiltration, while allowing researchers to execute their tasks.
The airlock feature brings several actions: ingress/egress Mechanism; Data movement ; Security gates; Approval mechanism; Notifications. And as part of TRE's Safe settings all activity must be tracked for auditiing purpose.

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
b. **In-progress**: The import/export process has now started and is in-progress.
c. **Approved**: The import/export process has been approved. At this state, data has been securely verified and manually reviewed. The data is now in its final location. For an import process the data is now available in the TRE workspace. It can be accessed by the requestor from within the workspace.
d. **Rejected**: The import/export process has been rejected. The data in the process was rejected manually by the Airlock Manager.
e. **Blocked**: The import/export process has been blocked. The security analysis found issues in the submitted data, and consequently quarantined the data.
f. **Cancelled**: The import/export process was manually cancelled by the requestor TRE user, a Workspace owner or a TRE administrator.

When an airlock process is created the state is `Draft` and the user gets a storage location (storage account -> SAS token + URL) he can use to place the date to be processed (import or export). This storage location is external for import (`stalimex`) or internal for export (`stalexint`), however only accessible to the requestor (ex: a TRE user/researcher).
The user will be able to upload a file to the provided storage location.

The user Submits the request (TRE API call) starting the data movement (to the `stalimip` - import in-progress or `stalexip` - export in-progress). If enabled, the Security Scanning is started wither identifying security flaws or not.
When the process is concluded, if no security flaws were identified, a notification is sent to the Data workspace Steward users providing the access to data (SAS token + URL with READ permission).
In case security flaws are found, the data is moved to storage rejected (either rejected import `stalimrej` or rejected export `stalexrej`).

The Data Stewards will manually review the data using the tools of their choice available in the TRE workspace. Once review is completed, the Data Stewards will have to **approve** or **reject** the airlock proces, though a TRE API call. This call will start the data movement to the final storage destination: `stalexapp` - external approved export or `stalimapp` - internal approved import.
There is also a state update, which will trigger a notification to the requestor including a SAS token + URL for the containers holding the data.

## Data movement

For any airlock process there is data movement either **into** a TRE workspace (in import process) or **from** a TRE workspace (in export process). Being the TRE a Workspace boundary, there are networking configurations designed to achieve this goal. The data movement will guarantee that the data is automatically verified for securty flaws and manually reviewed, before placing data inside the TRE Workspace.
Also, the process guarantees that data is not tampered with through out the process.

In an import process, data will transition from more public locations (yet confined to the requestor) to TRE workspace storage, after guaranteeding security automatically and by manual review.

In an export process data will transition from internal locations (available to the requetor) to public locations in the TRE, after going through a manual review.

> The data movement mechanism is data-driven, allowing an organization to extend how request data transitions between

## Security Scan

The identified data in a airlock proces, will be submited to a security scan. If the security scan identifies issues the data is quarantine, and a report is added to the process metadata. Both the requestor and Workspace Owner are notified. For successful security scan, the data will remain in state **In-progress**, and accessible to the Workspace Owner.

> * The Security scan will be optional, behind a feature flag, enabled by script
> * The outcome of security scan will be either the in-progress (`stalexip`) storage or rejected (`stalexrej`)
> * An airlock process will guarantee that the content being imported/exported is secure. It is envisioned that a set of **security gates** are identified to be executed successfully for a process to be approve.

## Approval mechanism

The approval mechanism, is bundled with any airlock process, providing a specific way to `approve` or `reject` the data. This mechanism will allow the Data Stewards to explicitly approve/reject the process, after having acess to the data. The Data Steward users will be able to execute a manual review on the data using the tools available to him in the TRE Workspace. Once this manual review is executed

The only responsability of the Approval mechanism is to support a cycle of revision, approval or rejection, while tracking the decision.

This mechanism will provice access to the data in the airlock process, and will be able to use a VM in TRE workspace. The data review will be the Data Steward responsability

> * It is envisioned that this mechanism to be more flexible and extensible.
> * The `Data Steward` is a role defined at workspace instance level and assigned to identities. Initially the `Owner` role will be used.

## Notifications

Throughout the airlock process, the notification mechanism will notify the relevant people to the process. Both the requestor (TRE User/Researcher) and the Workspace Owner will be notified by email, of the relevant process events.

Whenever the airlock process changes to a state of `Draft`, `Submitted`, `Approved`, `Rejected`, `Blocked`, the process requestor gets notified.
When the state changes to `In-progress` the Workspace Onwer (Data Steward) gets notified.

> * The Notification mechanism is also data-driven, allowing an organization to extend the notifications behavior. The mechanism is exemplified with a Logic App determining the notifications logic.
> * Notifications will work with All TRE users being AAD users (guests or not), with email defined – if not, notifications will not be sent.

### Architecture

The Airlock feature is supported by infrastructure at the TRE and workspace level.

TRE:
<<<<<<< HEAD
* `stalexapp` - storage (st) airlock (al) export (ex) approved (app)
* `stalimex` - storage (st) airlock (al) import (im) external (ex)
* `stalimip` - storage (st) airlock (al) import (im) in-progress (ip)
* `stalimrej` - storage (st) airlock (al) import (im) rejected (rej)
=======
* `stalexapp` - storage (st) airlock (al) approved (app) export (ex)
* `stalimex` - storage (st) airlock (al) external (ex) import (im)
* `stalimip` - storage (st) airlock (al) import (im) in-progress (ip)
* `stalimrej` - storage (st) airlock (al) rejected (rej) import (im)
>>>>>>> Linter review + stg names

Workspace
* `stalexint` - workspace storage (st) airlock (al) export (ex) internal (int)
* `stalexip` - workspace storage (st) airlock (al) export (ex) in-progress (ip)
* `stalexrej` - workspace storage (st) airlock (al) export (ex) rejected (rej)
* `stalimapp` - workspace storage (st) airlock (al) import (im) approved (app)

> * The external storage accounts (`stalimex`, `stalexapp`), are not bound to any vnet and accessible (with SAS token) via internet.
> * The internal storage account (`stalexint`) is bound to the workspace vnet, so ONLY TRE Users/Researchers on that workspace can access it
> * The (import) in-progress storage account (`stalimip`) is bound to the TRE CORE vnet
> * The (export) in-progress storage account (`stalexip`) is bound to the workspace vnet
> * The (import) rejected storage account (`stalimrej`) is bound to the TRE CORE vnet
> * The (export) rejected storage account (`stalexrej`) is bound to the TRE CORE vnet
> * The (import) approved storage account (`stalimapp`) is bound to the workspace vnet
