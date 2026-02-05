# Revised Airlock Architecture - ABAC with Private Endpoint-Based Access Control

## New Understanding: ABAC Can Filter by Private Endpoint Source!

**Key Insight from Microsoft Docs:**
ABAC conditions can restrict access based on **which private endpoint** the request comes from, using:
```hcl
@Request[Microsoft.Network/privateEndpoints] StringEquals '/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/privateEndpoints/{pe-name}'
```

This enables:
- ✅ One consolidated storage account
- ✅ Multiple private endpoints to that storage account (from different VNets/subnets)
- ✅ ABAC controls which PE can access which containers
- ✅ Combined with metadata stage filtering for defense-in-depth

## Revised Architecture - TRUE Consolidation

### Core: TWO Storage Accounts (Down from 6)

**Account 1: stalimex{tre_id} - Import External (PUBLIC)**
- Network: Public access (no VNet binding)
- Purpose: Researchers upload import data from internet
- Access: SAS tokens only
- Consolidation: Cannot merge (public vs. private)

**Account 2: stalairlock{tre_id} - Core Consolidated (PRIVATE)**
- Network: Private endpoints from multiple sources
- Contains stages: import-in-progress, import-rejected, import-blocked, export-approved
- Private Endpoints:
  1. PE from airlock_storage_subnet (for processor)
  2. PE from import-review workspace VNet (for Airlock Manager)
  3. Public access disabled
- ABAC controls which PE can access which stage containers

### Workspace: ONE Storage Account per Workspace (Down from 5)

**Account: stalairlockws{ws_id} - Workspace Consolidated (PRIVATE)**
- Network: Private endpoints from workspace services subnet
- Contains stages: export-internal, export-in-progress, export-rejected, export-blocked, import-approved
- Private Endpoints:
  1. PE from workspace services_subnet (for researchers and managers)
- ABAC controls who can access which stage containers

### External Storage for Export Approved

**Wait** - Export approved also needs public access for researchers to download!

### ACTUALLY: THREE Core Storage Accounts (Down from 6)

**Account 1: stalimex{tre_id} - Import External (PUBLIC)**
- For: Import draft uploads
- Public access with SAS tokens

**Account 2: stalairlock{tre_id} - Core Consolidated (PRIVATE)**
- For: Import in-progress, import-rejected, import-blocked
- Private endpoints with ABAC

**Account 3: stalexapp{tre_id} - Export Approved (PUBLIC)**
- For: Export approved downloads
- Public access with SAS tokens

**Result for 10 workspaces:**
- Before: 56 storage accounts
- After: 3 core + 10 workspace = 13 storage accounts
- **Reduction: 77%**

## ABAC with Private Endpoint Filtering

### Core Consolidated Storage (stalairlock)

**Multiple Private Endpoints:**
1. **PE from airlock_storage_subnet** (processor access)
2. **PE from import-review workspace VNet** (manager review access)

**ABAC Conditions:**

**Processor Identity (from airlock_storage_subnet PE):**
```hcl
# No restrictions - full access via airlock PE
resource "azurerm_role_assignment" "airlock_core_blob_data_contributor" {
  scope                = azurerm_storage_account.sa_airlock_core.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.airlock_id.principal_id
  # No ABAC condition - full access
}
```

**Review Workspace Identity (from review workspace PE):**
```hcl
# Restricted to import-in-progress stage only via review workspace PE
resource "azurerm_role_assignment" "review_workspace_import_access" {
  scope                = azurerm_storage_account.sa_airlock_core.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = data.azurerm_user_assigned_identity.review_workspace_id.principal_id
  
  condition_version = "2.0"
  condition         = <<-EOT
    (
      @Request[Microsoft.Network/privateEndpoints] StringEquals 
        '/subscriptions/${var.subscription_id}/resourceGroups/${var.ws_resource_group_name}/providers/Microsoft.Network/privateEndpoints/pe-import-review-${var.short_workspace_id}'
      AND
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
        StringEquals 'import-in-progress'
    )
  EOT
}
```

**API Identity:**
```hcl
# Restricted to import-in-progress stage via core API PE
resource "azurerm_role_assignment" "api_core_blob_data_contributor" {
  scope                = azurerm_storage_account.sa_airlock_core.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.api_id.principal_id
  
  condition_version = "2.0"
  condition         = <<-EOT
    (
      !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'} 
        OR ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'}
        OR ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'})
      OR
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
        StringIn ('import-in-progress')
    )
  EOT
}
```

### Workspace Consolidated Storage (stalairlockws)

**Private Endpoint:**
1. PE from workspace services_subnet

**ABAC Conditions:**

**Researcher Identity:**
```hcl
# Restricted to export-internal and import-approved only
resource "azurerm_role_assignment" "researcher_workspace_access" {
  scope                = azurerm_storage_account.sa_airlock_workspace.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.researcher_id.principal_id
  
  condition_version = "2.0"
  condition         = <<-EOT
    (
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
        StringIn ('export-internal', 'import-approved')
    )
  EOT
}
```

**Airlock Manager Identity:**
```hcl
# Can access export-in-progress for review
resource "azurerm_role_assignment" "manager_workspace_review_access" {
  scope                = azurerm_storage_account.sa_airlock_workspace.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = data.azurerm_user_assigned_identity.manager_id.principal_id
  
  condition_version = "2.0"
  condition         = <<-EOT
    (
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
        StringIn ('export-in-progress', 'export-internal')
    )
  EOT
}
```

## Access Control Matrix

### Import Flow

| Stage | Storage Account | Network Access | Researcher | Airlock Manager | Processor | API |
|-------|----------------|----------------|------------|----------------|-----------|-----|
| Draft (external) | stalimex | Public + SAS | ✅ Upload | ❌ | ✅ | ✅ |
| In-Progress | stalairlock | Core VNet PE | ❌ | ✅ Review (via review WS PE) | ✅ | ✅ |
| Rejected | stalairlock | Core VNet PE | ❌ | ✅ Audit | ✅ | ❌ ABAC blocks |
| Blocked | stalairlock | Core VNet PE | ❌ | ✅ Audit | ✅ | ❌ ABAC blocks |
| Approved | stalairlockws | Workspace VNet PE | ✅ Access (ABAC) | ❌ | ✅ | ✅ |

### Export Flow

| Stage | Storage Account | Network Access | Researcher | Airlock Manager | Processor | API |
|-------|----------------|----------------|------------|----------------|-----------|-----|
| Draft (internal) | stalairlockws | Workspace VNet PE | ✅ Upload (ABAC) | ✅ View | ✅ | ✅ |
| In-Progress | stalairlockws | Workspace VNet PE | ❌ ABAC blocks | ✅ Review (ABAC) | ✅ | ✅ |
| Rejected | stalairlockws | Workspace VNet PE | ❌ ABAC blocks | ✅ Audit | ✅ | ❌ ABAC blocks |
| Blocked | stalairlockws | Workspace VNet PE | ❌ ABAC blocks | ✅ Audit | ✅ | ❌ ABAC blocks |
| Approved | stalexapp | Public + SAS | ✅ Download | ❌ | ✅ | ✅ |

## Key Security Controls

### 1. Network Layer (Private Endpoints)
- Different VNets connect via different PEs
- stalairlock has PE from: airlock_storage_subnet + import-review workspace
- stalairlockws has PE from: workspace services_subnet
- Public accounts (stalimex, stalexapp) accessible via internet with SAS

### 2. ABAC Layer (Metadata + Private Endpoint)
- Combines metadata stage with source private endpoint
- Ensures correct identity from correct network location
- Example: Review workspace can only access import-in-progress from its specific PE

### 3. SAS Token Layer
- Time-limited tokens
- Container-scoped
- Researcher access to draft and approved stages

## Revised Cost Savings

### Storage Accounts
**Before:** 56 accounts
**After:** 13 accounts (3 core + 10 workspace)
- stalimex (1)
- stalairlock (1) - consolidates 3 core accounts
- stalexapp (1)
- stalairlockws × 10 workspaces - consolidates 5 accounts each

**Reduction: 77%**

### Private Endpoints
**Before:** 55 PEs
**After:** 13 PEs
- stalimex: 0 (public)
- stalairlock: 2 (airlock subnet + import-review workspace subnet)
- stalexapp: 0 (public)
- stalairlockws × 10: 1 each = 10

**Reduction: 76%**

### Monthly Cost (10 workspaces)
**Before:**
- 55 PEs × $7.30 = $401.50
- 56 accounts × $10 Defender = $560
- Total: $961.50/month

**After:**
- 13 PEs × $7.30 = $94.90
- 13 accounts × $10 Defender = $130
- Total: $224.90/month

**Savings: $736.60/month = $8,839/year**

## Implementation Updates Required

### 1. Core Storage - Keep External and Approved Separate

Update `/core/terraform/airlock/storage_accounts.tf`:
- Keep `sa_import_external` (public access)
- Keep `sa_export_approved` (public access)
- Update `sa_airlock_core` to consolidate only: in-progress, rejected, blocked
- Add second private endpoint for import-review workspace access
- Add ABAC condition combining PE source + metadata stage

### 2. Import Review Workspace

Update `/templates/workspaces/airlock-import-review/terraform/import_review_resources.terraform`:
- Change storage account reference to `stalairlock{tre_id}`
- Update PE configuration
- Add ABAC condition restricting to import-in-progress only

### 3. ABAC Conditions - PE + Metadata Combined

**Example for Review Workspace:**
```hcl
condition = <<-EOT
  (
    @Request[Microsoft.Network/privateEndpoints] StringEquals 
      '/subscriptions/${var.subscription_id}/resourceGroups/rg-${var.tre_id}-ws-${var.review_workspace_id}/providers/Microsoft.Network/privateEndpoints/pe-import-review-${var.review_workspace_id}'
    AND
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
      StringEquals 'import-in-progress'
  )
EOT
```

This ensures:
- Access only via specific PE (from review workspace)
- Access only to containers with stage = import-in-progress
- Double security layer!

### 4. Helper Functions

Update to return correct accounts:
- Import draft → stalimex (public)
- Import in-progress/rejected/blocked → stalairlock (private)
- Import approved → stalairlockws (private)
- Export draft/in-progress/rejected/blocked → stalairlockws (private)
- Export approved → stalexapp (public)

## Conclusion

The consolidation can still achieve excellent results:
- **13 storage accounts** (down from 56) = 77% reduction
- **13 private endpoints** (down from 55) = 76% reduction
- **$737/month savings** = $8,839/year
- **ABAC provides fine-grained control** combining PE source + metadata stage
- **All security requirements maintained**

This approach:
✅ Maintains network isolation (public vs. private)
✅ Uses ABAC for container-level access control
✅ Supports import review workspace
✅ Keeps researcher access restrictions
✅ Achieves significant cost savings
