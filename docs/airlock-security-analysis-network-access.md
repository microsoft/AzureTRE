# Airlock Security Analysis - Network Access and ABAC

## Critical Security Requirement

**Researchers must only access storage containers when in the appropriate stage.**

This is enforced through a combination of:
1. Network access controls (VNet binding via private endpoints)
2. ABAC conditions (stage-based permissions)
3. SAS token generation (scoped to specific containers)

## Network Access Matrix - Original Design

### Import Flow

| Stage | Storage Account | Network Access | Who Can Access |
|-------|----------------|----------------|----------------|
| Draft (external) | `stalimex` | **NOT bound to VNet** (public with SAS) | Researcher (via SAS token from internet) |
| In-Progress | `stalimip` | Bound to **TRE CORE VNet** | Airlock Manager (via review workspace), Processor |
| Rejected | `stalimrej` | Bound to **TRE CORE VNet** | Airlock Manager (for investigation), Processor |
| Blocked | `stalimblocked` | Bound to **TRE CORE VNet** | Airlock Manager (for investigation), Processor |
| Approved | `stalimapp` | Bound to **Workspace VNet** | Researcher (from within workspace), Processor |

### Export Flow

| Stage | Storage Account | Network Access | Who Can Access |
|-------|----------------|----------------|----------------|
| Draft (internal) | `stalexint` | Bound to **Workspace VNet** | Researcher (from within workspace) |
| In-Progress | `stalexip` | Bound to **Workspace VNet** | Airlock Manager (from workspace), Processor |
| Rejected | `stalexrej` | Bound to **Workspace VNet** | Airlock Manager (from workspace), Processor |
| Blocked | `stalexblocked` | Bound to **Workspace VNet** | Airlock Manager (from workspace), Processor |
| Approved | `stalexapp` | **NOT bound to VNet** (public with SAS) | Researcher (via SAS token from internet) |

## PROBLEM: Consolidated Storage Network Configuration

**The Issue:**
With consolidated storage, we have:
- 1 core storage account for: external, in-progress, rejected, blocked, export-approved
- 1 workspace storage account for: internal, in-progress, rejected, blocked, import-approved

**Network Problem:**
- A storage account can only have ONE network configuration
- `stalimex` needs to be public (for researcher upload via internet)
- `stalimip` needs to be on TRE CORE VNet (for review workspace access)
- **Both cannot exist in the same storage account with different network configs!**

## SOLUTION: Keep TWO Core Storage Accounts

We need to maintain network isolation. Revised consolidation:

### Core Storage Accounts (2 instead of 1)

**Account 1: External Access - `stalimex{tre_id}` (NO change)**
- Network: Public access (with firewall restrictions)
- Stages: import-external (draft)
- Access: Researchers via SAS token from internet
- **Cannot consolidate** - needs public access

**Account 2: Core Internal - `stalairlock{tre_id}` (NEW consolidated)**
- Network: Bound to TRE CORE VNet via private endpoint
- Stages: import-in-progress, import-rejected, import-blocked, export-approved
- Access: Airlock Manager (review workspace), Processor, API
- **Consolidates 4 accounts → 1**

### Workspace Storage Accounts (2 instead of 1)

**Account 1: Workspace Internal - `stalairlockws{ws_id}` (NEW consolidated)**
- Network: Bound to Workspace VNet via private endpoint
- Stages: export-internal, export-in-progress, export-rejected, export-blocked, import-approved
- Access: Researchers (from workspace), Airlock Manager, Processor
- **Consolidates 5 accounts → 1**

**Account 2: Export Approved - `stalexapp{tre_id}` (NO change)**
- Network: Public access (with firewall restrictions)
- Stages: export-approved (final)
- Access: Researchers via SAS token from internet
- **Cannot consolidate** - needs public access

## Revised Consolidation Numbers

### Before
- Core: 6 storage accounts, 5 private endpoints
- Per workspace: 5 storage accounts, 5 private endpoints
- Total for 10 workspaces: 56 storage accounts, 55 private endpoints

### After (Revised)
- Core: 3 storage accounts (stalimex, stalairlock, stalexapp), 1 private endpoint
- Per workspace: 1 storage account (stalairlockws), 1 private endpoint
- Total for 10 workspaces: 13 storage accounts, 11 private endpoints

### Impact
- **Storage accounts:** 56 → 13 (77% reduction, was 79%)
- **Private endpoints:** 55 → 11 (80% reduction, unchanged)
- **Monthly savings:** ~$747 (was $761)
- **Annual savings:** ~$8,964 (was $9,134)

**Still excellent savings!** The slight reduction in savings is worth it to maintain proper network security boundaries.

## Revised Architecture

### Core Storage

**stalimex{tre_id} - Import External (UNCHANGED):**
- Network: Public + firewall rules
- Private Endpoint: No
- Container: {request_id}
- Metadata: {"stage": "import-external"}
- Access: Researcher via SAS token (from internet)

**stalairlock{tre_id} - Core Consolidated (NEW):**
- Network: Private (TRE CORE VNet)
- Private Endpoint: Yes (on airlock_storage_subnet_id)
- Containers: {request_id} with metadata stage values:
  - "import-in-progress"
  - "import-rejected"  
  - "import-blocked"
- Access: Airlock Manager (review workspace PE), Processor, API
- ABAC: API restricted to import-in-progress only

**stalexapp{tre_id} - Export Approved (UNCHANGED):**
- Network: Public + firewall rules
- Private Endpoint: No
- Container: {request_id}
- Metadata: {"stage": "export-approved"}
- Access: Researcher via SAS token (from internet)

### Workspace Storage

**stalairlockws{ws_id} - Workspace Consolidated (NEW):**
- Network: Private (Workspace VNet)
- Private Endpoint: Yes (on services_subnet_id)
- Containers: {request_id} with metadata stage values:
  - "export-internal"
  - "export-in-progress"
  - "export-rejected"
  - "export-blocked"
  - "import-approved"
- Access: Researchers (from workspace), Airlock Manager, Processor, API
- ABAC: Different conditions for researchers vs. API

## Import Review Workspace

### Purpose
Special workspace where Airlock Managers review import requests before approval.

### Configuration
- Has private endpoint to **stalairlock{tre_id}** (core consolidated storage)
- Airlock Manager can access containers with stage "import-in-progress"
- Network isolated - can only access via private endpoint from review workspace

### Update Required
`templates/workspaces/airlock-import-review/terraform/import_review_resources.terraform`:
- Change reference from `stalimip` to `stalairlock{tre_id}`
- Update private endpoint and DNS configuration
- ABAC on review workspace service principal to restrict to "import-in-progress" only

## ABAC Access Control - Revised

### Core Storage Account (stalairlock{tre_id})

**API Identity:**
```hcl
condition = <<-EOT
  @Resource[...containers].metadata['stage'] 
    StringIn ('import-in-progress')
EOT
```
- Access: import-in-progress only
- Blocked: import-rejected, import-blocked

**Airlock Manager (Review Workspace Service Principal):**
```hcl
condition = <<-EOT
  @Resource[...containers].metadata['stage'] 
    StringEquals 'import-in-progress'
EOT
```
- Access: import-in-progress only (READ only)
- Purpose: Review data before approval

**Airlock Processor:**
- No ABAC restrictions
- Full access to all stages

### Workspace Storage Account (stalairlockws{ws_id})

**Researcher Identity:**
```hcl
condition = <<-EOT
  @Resource[...containers].metadata['stage'] 
    StringIn ('export-internal', 'import-approved')
EOT
```
- Access: export-internal (draft export), import-approved (final import)
- Blocked: export-in-progress, export-rejected, export-blocked (review stages)

**API Identity:**
```hcl
condition = <<-EOT
  @Resource[...containers].metadata['stage'] 
    StringIn ('export-internal', 'export-in-progress', 'import-approved')
EOT
```
- Access: All operational stages
- Blocked: None (API manages all workspace stages)

**Airlock Processor:**
- No ABAC restrictions
- Full access to all stages

## Stage Access Matrix

### Import Flow

| Stage | Storage | Network | Researcher Access | Airlock Manager Access | Notes |
|-------|---------|---------|-------------------|----------------------|-------|
| Draft (external) | stalimex | Public | ✅ Upload (SAS) | ❌ No | Upload from internet |
| In-Progress | stalairlock | Core VNet | ❌ No | ✅ Review (via review WS) | Manager reviews in special workspace |
| Rejected | stalairlock | Core VNet | ❌ No | ✅ View (for audit) | Kept for investigation |
| Blocked | stalairlock | Core VNet | ❌ No | ✅ View (for audit) | Malware found, quarantined |
| Approved | stalairlockws | Workspace VNet | ✅ Access (from WS) | ❌ No | Final location, researcher can use |

### Export Flow

| Stage | Storage | Network | Researcher Access | Airlock Manager Access | Notes |
|-------|---------|---------|-------------------|----------------------|-------|
| Draft (internal) | stalairlockws | Workspace VNet | ✅ Upload (from WS) | ❌ No | Upload from within workspace |
| In-Progress | stalairlockws | Workspace VNet | ❌ No | ✅ Review (from WS) | Manager reviews in same workspace |
| Rejected | stalairlockws | Workspace VNet | ❌ No | ✅ View (for audit) | Kept for investigation |
| Blocked | stalairlockws | Workspace VNet | ❌ No | ✅ View (for audit) | Malware found, quarantined |
| Approved | stalexapp | Public | ✅ Download (SAS) | ❌ No | Download from internet |

## SAS Token Generation

### Researcher Access (Draft Stages)

**Import Draft:**
```python
# API generates SAS token for stalimex container
token = generate_sas_token(
    account="stalimex{tre_id}",
    container=request_id,
    permission="write"  # Upload only
)
# Researcher accesses from internet
```

**Export Draft:**
```python
# API generates SAS token for stalairlockws container
# ABAC ensures only export-internal stage is accessible
token = generate_sas_token(
    account="stalairlockws{ws_id}",
    container=request_id,
    permission="write"  # Upload only
)
# Researcher accesses from workspace VMs
```

### Researcher Access (Approved Stages)

**Import Approved:**
```python
# API generates SAS token for stalairlockws container
# ABAC ensures only import-approved stage is accessible
token = generate_sas_token(
    account="stalairlockws{ws_id}",
    container=request_id,
    permission="read"  # Download only
)
# Researcher accesses from workspace VMs
```

**Export Approved:**
```python
# API generates SAS token for stalexapp container
token = generate_sas_token(
    account="stalexapp{tre_id}",
    container=request_id,
    permission="read"  # Download only
)
# Researcher accesses from internet
```

### Airlock Manager Access (Review Stages)

**Import Review (In-Progress):**
- Network: Private endpoint from airlock-import-review workspace to stalairlock
- ABAC: Restricted to import-in-progress stage only
- Access: READ only via review workspace VMs
- No SAS token needed - uses service principal with ABAC

**Export Review (In-Progress):**
- Network: Already in same workspace VNet (stalairlockws)
- ABAC: Airlock Manager role has access to export-in-progress
- Access: READ only via workspace VMs
- No SAS token needed - uses workspace identity with ABAC

## Security Guarantees Maintained

### 1. Researcher Upload Isolation
✅ **Import draft:** Public storage account (stalimex) with SAS token scoped to their container only
✅ **Export draft:** Workspace storage (stalairlockws) with ABAC restricting to export-internal stage

### 2. Review Stage Isolation
✅ **Import in-progress:** Core storage (stalairlock) accessible only from review workspace via PE + ABAC
✅ **Export in-progress:** Workspace storage (stalairlockws) with ABAC restricting access

### 3. Blocked/Rejected Quarantine
✅ **Import blocked/rejected:** Core storage (stalairlock), no researcher access, manager can view for audit
✅ **Export blocked/rejected:** Workspace storage (stalairlockws), no researcher access, manager can view for audit

### 4. Approved Data Access
✅ **Import approved:** Workspace storage (stalairlockws), researcher accesses from workspace with ABAC
✅ **Export approved:** Public storage (stalexapp) with SAS token for download

## Updates Required

### 1. Terraform - Keep External/Approved Storage Separate

**Core storage_accounts.tf:**
- Keep `stalimex` as separate storage account (public access)
- Keep `stalexapp` as separate storage account (public access)
- Consolidate only: stalimip, stalimrej, stalimblocked into `stalairlock`

### 2. Import Review Workspace

**airlock-import-review/terraform/import_review_resources.terraform:**
- Update reference from `stalimip` to `stalairlock{tre_id}`
- Update private endpoint name and DNS zone
- Add ABAC condition for review workspace service principal (import-in-progress only)

### 3. Constants

Update to reflect revised architecture:
- Keep: STORAGE_ACCOUNT_NAME_IMPORT_EXTERNAL, STORAGE_ACCOUNT_NAME_EXPORT_APPROVED
- Add: STORAGE_ACCOUNT_NAME_AIRLOCK_CORE (consolidates in-progress, rejected, blocked)
- Keep: STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE (consolidates internal, in-progress, rejected, blocked, approved)

### 4. Storage Helper Functions

Update logic to return correct storage accounts:
- Draft import → stalimex (external, public)
- Submitted/review/rejected/blocked import → stalairlock (core, private)
- Approved import → stalairlockws (workspace, private)
- Draft export → stalairlockws (workspace, private)
- Submitted/review/rejected/blocked export → stalairlockws (workspace, private)
- Approved export → stalexapp (public)

## Revised Cost Savings

### Before
- Core: 6 storage accounts, 5 private endpoints
- Per workspace: 5 storage accounts, 5 private endpoints
- Total for 10 workspaces: 56 accounts, 55 PEs
- Cost: $961.50/month

### After (Revised)
- Core: 3 storage accounts (stalimex, stalairlock, stalexapp), 1 private endpoint
- Per workspace: 1 storage account (stalairlockws), 1 private endpoint
- Total for 10 workspaces: 13 accounts, 11 PEs
- Cost: $224.30/month

### Savings
- **$737.20/month** (was $761.20)
- **$8,846/year** (was $9,134)
- **Still 77% reduction in storage accounts**
- **Still 80% reduction in private endpoints**

## Security Benefits of Revised Design

### Network Isolation Maintained
✅ Public stages (import draft, export approved) remain isolated
✅ Private stages (in-progress, rejected, blocked) remain on private VNets
✅ Workspace boundary preserved
✅ Review workspace can still access import in-progress via private endpoint

### ABAC Adds Additional Layer
✅ Even with network access, ABAC restricts by container metadata stage
✅ API can only access operational stages
✅ Researchers can only access appropriate stages via ABAC on their identities
✅ Review workspace restricted to in-progress only via ABAC

### Defense in Depth
1. **Network:** Private endpoints for internal stages, public with SAS for external
2. **ABAC:** Stage-based access restrictions on role assignments
3. **SAS Tokens:** Time-limited, container-scoped access for researchers
4. **RBAC:** Role-based permissions for identities

## Recommendation

**Revise the implementation to maintain 4 separate storage accounts:**
1. `stalimex` - Import external (public, separate)
2. `stalairlock` - Core consolidated (private: in-progress, rejected, blocked for import)
3. `stalexapp` - Export approved (public, separate)
4. `stalairlockws` - Workspace consolidated (private: all workspace stages)

This provides:
- ✅ Proper network isolation for public vs. private stages
- ✅ Significant cost savings (77% reduction)
- ✅ ABAC for additional security
- ✅ Import review workspace compatibility
- ✅ Researcher access control maintained
