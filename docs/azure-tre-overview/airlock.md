# Airlock

In a Trusted Research Environment (TRE) the workspaces represent a security boundary that enables researchers to access data, execute analysis, apply algorithms and collect reports. The airlock capability is the only mechanism that allows users to `import` or `export` data, tools or other file based artefacts in a secure fashion with a human approval.
This constitutes the mechanism focused on preventing data exfiltration and securing TRE and its workspaces from inappropriate data, while allowing researchers to work on their projects and execute their tasks.
The airlock feature brings several actions: ingress/egress Mechanism; Data movement; Security gates; Approval mechanism and Notifications. As part of TRE's Safe settings all activity must be tracked for auditing purposes.

The Airlock feature aims to address these goals:

* Prevent unauthorised data import or export.

* Provide a process to allow approved data to be imported through the security boundary of a TRE Workspace.

* TRE provides functionality to track requests and decisions, supporting cycles of revision, approval or rejection.

* Data being imported with an airlock import process can be automatically scanned for security issues.

* Data being exported or imported must be manually reviewed by the Airlock Manager.

* Notify the requesting researcher of the process progress and/or required actions.

* All steps within the airlock process are audited.

Typically in a TRE, the Airlock feature would be used to allow a researcher to export the outputs of a research project such as summary results. With the airlock, data to be exported must go through a human review, typically undertaken by a data governance team.

The Airlock feature will create events on every meaningful step of the process. This will enable increased flexibility by allowing an organization to extend the notification mechanism.

## Ingress/Egress Mechanism

The Airlock allows a TRE user to start the `import` or `export` process to a given workspace. A number of milestones must be reached in order to complete a successful import or export. These milestones are defined using the following states:

1. **Draft**: An Airlock request has been created but has not yet started. The TRE User/Researcher has now access to a storage location and they must identify the data to be processed. At this point the airlock import/export processes allow a single file to be processed. However a compressed file may be used (zip).
2. **Submitted**: The request was submitted by the researcher (not yet processed).
3. **In-Review**: The request is ready to be reviewed. This state can be reached directly from Submitted state or after going through a successful security scan (found clean).
4. **Approval In-progress**: The Airlock request has been approved, however data movement is still ongoing.
5. **Approved**: The Airlock request has been approved. At this state, data has been securely verified and manually reviewed. The data is now in its final location. For an import process the data is now available in the TRE workspace, it can be accessed by the requestor from within the workspace.
6. **Rejection In-progress**: The Airlock request has been rejected, however data movement is still ongoing.
7. **Rejected**: The Airlock request has been rejected. The data in the process was rejected manually by the Airlock Manager.
8. **Cancelled**: The Airlock request was manually cancelled by the requestor TRE user, a Workspace owner or a TRE administrator. The cancelation is only allowed when the request is not actively changing (i.e. **Draft** or **In-Review** state).
9. **Blocking In-progress**: The Airlock request has been blocked, however data movement is still ongoing.
10. **Blocked By Scan**: The Airlock request has been blocked. The security analysis found issues in the submitted data and consequently quarantined the data.

```mermaid
graph TD 
  A[Researcher wants to export data from TRE Workspace] -->|Request created| B[Request in state Draft] 
  B-->|Researcher gets link to storage container and uploads data| B
  B-->|Request submitted| C[Submitted]
  C--> D{Security issues found?} 
  D-->|Yes| E[Blocking In-progress]
  D-->|No| G[In-Review]
  E:::temporary--> F((Blocked By Scan))
  G-->|Human Review| H{Is data appropriate to export?}
  H-->|Approve| I[Approval In-progress]
  H-->|Reject| J[Rejection In-progress]
  I:::temporary-->K((Approved))
  J:::temporary-->L((Rejected))
  B-->|Request Canceled| X((Canceled))
  G-->|Request Canceled| X
  H-->|Request Canceled| X
  classDef temporary stroke-dasharray: 5 5
```
> Airlock state flow diagram for an Airlock export request

When an airlock process is created the initial state is **Draft** and the required infrastructure will get created providing a single container to isolate the data in the request. Once completed, the user will be able to get a link for this container inside the storage account (URL + SAS token) that they can use to upload the desired data to be processed (import or export).

This storage location is external for import (`stalimex`) or internal for export (`stalexint`), however only accessible to the requestor (ex: a TRE user/researcher).
The user will be able to upload a file to the provided storage location, using any tool of their preference: [Azure Storage Explorer](https://azure.microsoft.com/en-us/features/storage-explorer/) or [AzCopy](https://docs.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-v10) which is a command line tool.

The user Submits the request (TRE API call) starting the data movement (to the `stalimip` - import in-progress or `stalexip` - export in-progress). The airlock request is now in state **Submitted**.
If enabled, the Malware Scanning is started. The scan is done using Microsoft Defender for Storage, which is described in details [here](https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-storage-introduction).
In the case that security flaws are found, the request state becomes **Blocking In-progress** while the data is moved to blocked storage  (either import blocked `stalimblocked` or export blocked `stalexblocked`). In this case, the request is finalized with the state **Blocked By Scan**.
If the Security Scanning does not identify any security flaws, the request state becomes **In-Review**. Simultaneously, a notification is sent to the Airlock Manager user. The user needs to ask for the container URL using the TRE API (SAS token + URL with READ permission).

> The Security Scanning can be disabled, changing the request state from **Submitted** straight to **In-Review**.

The Airlock Manager will manually review the data using the tools of their choice available in the TRE workspace. Once review is completed, the Airlock Manager will have to *Approve* or *Reject* the airlock proces, though a TRE API call.
At this point, the request will change state to either **Approval In-progress** or **Rejection In-progress**, while the data movement occurs moving afterwards to **Approved** or **Rejected** accordingly. The data will now be in the final storage destination: `stalexapp` - export approved  or `stalimapp` - import approved.
With this state change, a notification will be triggered to the requestor including the location of the processed data in the form of an URL + SAS token.

## Data movement

For any airlock process, there is data movement either **into** a TRE workspace (in import process) or **from** a TRE workspace (in export process). Being a TRE Workspace boundary, there are networking configurations designed to achieve this goal. The data movement will guarantee that the data is automatically verified for security flaws and manually reviewed, before placing data inside the TRE Workspace.
Also, the process guarantees that data is not tampered with throughout the process.

In an import process, data will transition from more public locations (yet confined to the requestor) to TRE workspace storage, after guaranteeing security automatically and by manual review.

In an export process, data will transition from internal locations (available to the requestor) to public locations in the TRE, after going through a manual review.

Considering that the Airlock requests may require large data movements, the operations can have longer durations, hence becoming the operations asynchronous. This is why states like **Approval In-progress**, **Rejection In-progress** or **Blocking In-progress** will be set while there are data movement operations.

> The data movement mechanism is data-driven, allowing an organization to extend how request data transitions between

## Security Scan

The identified data in a airlock proces, will be submited to a security scan. If the security scan identifies issues the data is quarantined and a report is added to the process metadata. Both the requestor and Workspace Owner are notified. For a successful security scan, the data will remain in state **In-progress**, and accessible to the Workspace Owner.

> * The Security scan will be optional, behind a feature flag enabled by a script
> * The outcome of the security scan will be either the in-progress (`stalexip`) storage or blocked (`stalexblocked`)
> * An airlock process will guarantee that the content being imported/exported is secure. It is envisioned that a set of **security gates** are identified to be executed successfully for a process to be approved.

## Approval mechanism

The approval mechanism, is bundled with any airlock process, providing a specific way to `approve` or `reject` the data. This mechanism will allow the Airlock Managers to explicitly approve/reject the process, after having access to the data. The Airlock Manager users will be able to execute a manual review on the data using the tools available to them in a review TRE Workspace.
Once this manual review is executed, Airlock Managers can proactively approve or reject the airlock request.

The only goal of the Approval mechanism is to provide a cycle of revision, approval or rejection while tracking the decision.

This mechanism will provide access to the data in the airlock process, and will be able to use a VM in TRE workspace. The data review will be the Airlock Manager responsibility

> * It is envisioned that this mechanism to be more flexible and extensible.
> * The `Airlock Manager` is a role defined at the workspace instance level and assigned to identities. Initially, the `Owner` role will be used.

## Notifications

Throughout the airlock process, the notification mechanism will notify the relevant people of the process. Both the requestor (TRE User/Researcher) and the Workspace Owner will be notified by email of the relevant process events.

Whenever the airlock process changes to a state of **Draft**, **Submitted**, **Approved**, **Rejected**, **Approval In-progress**, **Rejection In-progress**, **Blocked By Scan** or **Cancelled**, the process requestor gets notified.
When the state changes to `In-progress` the Workspace Owner (Airlock Manager) gets notified.

> * The Notification mechanism is also data-driven, allowing an organization to extend the notifications behavior. The mechanism is exemplified with a Logic App determining the notifications logic.
> * Notifications will work with All TRE users being Microsoft Entra ID users (guests or not), with email defined – if not, notifications will not be sent.

## Architecture

The Airlock feature is supported by infrastructure at the TRE and workspace level, containing a set of storage accounts. Each Airlock request will provision and use unique storage containers with the request id in its name.

```mermaid
graph LR
  subgraph TRE Workspace
  E[(stalimapp</br>import approved)]
  end
  subgraph TRE
  A[(stalimex</br>import external)]-->|Request Submitted| B
  B[(stalimip</br>import in-progress)]-->|Security issues found| D[(stalimblocked</br>import blocked)] 
  B-->|No security issues found| review{Manual</br>Approval} 
  review-->|Rejected| C[(stalimrej</br>import rejected)]
  review-->|Approved| E
  end
  subgraph External
      data(Data to import)-->A
  end
```
> Data movement in an Airlock import request

```mermaid
graph LR
  subgraph TRE workspace
  data(Data to export)-->A
  A[(stalexint</br>export internal)]-->|Request Submitted| B
  B[(stalexip</br>export in-progress)]-->|Security issues found| D[(stalexblocked</br>export blocked)] 
  B-->|No security issues found| review{Manual</br>Approval} 
  review-->|Rejected| C[(stalexrej</br>export rejected)]
  end
  subgraph External
  review-->|Approved| E[(stalexapp</br>export approved)]
  end
```
> Data movement in an Airlock export request


TRE:

* `stalimex` - storage (st) airlock (al) import (im) external (ex)
* `stalimip` - storage (st) airlock (al) import (im) in-progress (ip)
* `stalimrej` - storage (st) airlock (al) import (im) rejected (rej)
* `stalimblocked` - storage (st) airlock (al) import (im) blocked
* `stalexapp` - storage (st) airlock (al) export (ex) approved (app)

Workspace:

* `stalimapp` - workspace storage (st) airlock (al) import (im) approved (app)
* `stalexint` - workspace storage (st) airlock (al) export (ex) internal (int)
* `stalexip` - workspace storage (st) airlock (al) export (ex) in-progress (ip)
* `stalexrej` - workspace storage (st) airlock (al) export (ex) rejected (rej)
* `stalexblocked` - workspace storage (st) airlock (al) export (ex) blocked

> * The external storage accounts (`stalimex`, `stalexapp`), are not bound to any vnet and are accessible (with SAS token) via the internet
> * The internal storage account (`stalexint`) is bound to the workspace vnet, so ONLY TRE Users/Researchers on that workspace can access it
> * The (export) in-progress storage account (`stalexip`) is bound to the workspace vnet
> * The (export) blocked storage account (`stalexblocked`) is bound to the workspace vnet
> * The (export) rejected storage account (`stalexrej`) is bound to the workspace vnet
> * The (import) in-progress storage account (`stalimip`) is bound to the TRE CORE vnet
> * The (import) blocked storage account (`stalimblocked`) is bound to the TRE CORE vnet
> * The (import) rejected storage account (`stalimrej`) is bound to the TRE CORE vnet
> * The (import) approved storage account (`stalimapp`) is bound to the workspace vnet

[![Airlock networking](../assets/airlock-networking.png)](../assets/airlock-networking.png)

In the TRE Core, the TRE API will provide the airlock API endpoints allowing to advance the process. The TRE API will expose the following methods:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/workspaces/{workspace_id}/requests` | Create an Airlock request (in **Draft**) |
| `POST` | `/api/workspaces/{workspace_id}/requests/{airlock_request_id}/link` | Get the url and token to access an Airlock Request | `POST` | `/api/workspaces/{workspace_id}/requests/{airlock_request_id}/submit` | Submits an Airlock request |
| `POST` | `/api/workspaces/{workspace_id}/requests/{airlock_request_id}/review` | Reviews an Airlock request |
| `POST` | `/api/workspaces/{workspace_id}/requests/{airlock_request_id}/cancel` | Cancels an Airlock request |


Also in the airlock feature there is the **Airlock Processor** which handles the events that are created throughout the process, signalling state changes from blobs created, status changed or security scans finalized.

## Airlock flow

The following sequence diagram detailing the Airlock feature and its event driven behaviour:

[![Airlock flow](../assets/airlock-swimlanes.png)](../assets/airlock-swimlanes.png)
