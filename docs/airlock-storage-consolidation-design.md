# Airlock Storage Account Consolidation Design

## Executive Summary

This document outlines the design for consolidating airlock storage accounts from 56 accounts (for 10 workspaces) to 12 accounts, reducing costs by approximately $763/month through reduced private endpoints and Defender scanning fees.

## Current Architecture

### Storage Accounts

**Core (6 accounts):**
- `stalimex{tre_id}` - Import External (draft stage)
- `stalimip{tre_id}` - Import In-Progress (scanning/review)
- `stalimrej{tre_id}` - Import Rejected
- `stalimblocked{tre_id}` - Import Blocked (malware found)
- `stalexapp{tre_id}` - Export Approved
- `stairlockp{tre_id}` - Airlock Processor (not consolidated)

**Per Workspace (5 accounts):**
- `stalimappws{ws_id}` - Import Approved
- `stalexintws{ws_id}` - Export Internal (draft stage)
- `stalexipws{ws_id}` - Export In-Progress (scanning/review)
- `stalexrejws{ws_id}` - Export Rejected
- `stalexblockedws{ws_id}` - Export Blocked (malware found)

### Private Endpoints
- Core: 5 PEs (all on `airlock_storage_subnet_id`, processor account has no PE on this subnet)
- Per Workspace: 5 PEs (all on `services_subnet_id`)

### Current Data Flow
1. Container created with `request_id` as name in source storage account
2. Data uploaded to container
3. On status change, data **copied** to new container (same `request_id`) in destination storage account
4. Source container deleted after successful copy

**Issues with Current Approach:**
- Data duplication during transitions
- Slow for large files
- Higher storage costs during transition periods
- Unnecessary I/O overhead

## Proposed Architecture

### Consolidated Storage Accounts

**Core:**
- `stalairlock{tre_id}` - Single consolidated account
  - Containers use prefix naming: `{stage}-{request_id}`
  - Stages: import-external, import-inprogress, import-rejected, import-blocked, export-approved
- `stairlockp{tre_id}` - Airlock Processor (unchanged)

**Per Workspace:**
- `stalairlockws{ws_id}` - Single consolidated account
  - Containers use prefix naming: `{stage}-{request_id}`
  - Stages: import-approved, export-internal, export-inprogress, export-rejected, export-blocked

### Private Endpoints
- Core: 1 PE (80% reduction from 5 to 1)
- Per Workspace: 1 PE per workspace (80% reduction from 5 to 1)

### New Data Flow (Metadata-Based Approach)
1. Container created with `{request_id}` as name in consolidated storage account
2. Container metadata set with `stage={current_stage}` (e.g., `stage=import-external`)
3. Data uploaded to container
4. On status change, container metadata **updated** to `stage={new_stage}` (e.g., `stage=import-inprogress`)
5. No data copying required - same container persists through all stages
6. ABAC conditions restrict access based on container metadata `stage` value

## Implementation Options

### Option A: Full Consolidation (Recommended)

**Pros:**
- Maximum cost savings
- Simpler infrastructure
- Easier to manage

**Cons:**
- Requires application code changes
- Migration complexity
- Testing effort

**Changes Required:**
1. **Infrastructure (Terraform):**
   - Replace 6 core storage accounts with 1
   - Replace 5 workspace storage accounts with 1 per workspace
   - Update private endpoints (5 → 1 for core, 5 → 1 per workspace)
   - Update EventGrid topic subscriptions
   - Update role assignments

2. **Application Code:**
   - Update `constants.py` to add consolidated account names and container prefixes
   - Update `get_account_by_request()` to return consolidated account name
   - Update `get_container_name_by_request()` (new function) to return prefixed container name
   - Update `create_container()` in `blob_operations.py` to use prefixed names
   - Update `copy_data()` to handle same-account copying
   - Update all references to storage account names

3. **Migration Path:**
   - Deploy new consolidated infrastructure alongside existing
   - Feature flag to enable new mode
   - Migrate existing requests to new structure
   - Decommission old infrastructure

### Option B: Metadata-Based Stage Management (RECOMMENDED - Updated)

**Pros:**
- Minimal application code changes
- No data copying overhead - fastest stage transitions
- Container names remain as `request_id` - minimal code changes
- Lower storage costs (no duplicate data during transitions)
- Better auditability - single container with full history
- ABAC provides fine-grained access control

**Cons:**
- Requires careful metadata management
- EventGrid integration needs adjustment
- Need to track stage history in metadata

**Changes Required:**
1. Keep `request_id` as container name
2. Add metadata `stage={stage_name}` to containers
3. Add metadata `stage_history` to track all stage transitions
4. Update stage by changing metadata instead of copying
5. Use ABAC conditions to restrict access based on `stage` metadata
6. Update EventGrid subscriptions to trigger on metadata changes
7. Add versioning or snapshot capability for compliance

**Benefits Over Copying:**
- ~90% faster stage transitions (no data movement)
- ~50% lower storage costs during transitions (no duplicate data)
- Simpler code (update metadata vs. copy blobs)
- Complete audit trail in single location

### Option C: Hybrid Approach

**Pros:**
- Balances cost savings with risk
- Allows phased rollout

**Cons:**
- More complex infrastructure
- Still requires most changes

**Changes Required:**
1. Start with core consolidation only (6 → 2: one for import, one for export)
2. Keep workspace accounts separate initially
3. Monitor and validate before workspace consolidation

## Cost Analysis

### Current Monthly Costs (10 workspaces)
- Storage Accounts: 56 total
- Private Endpoints: 55 × $7.30 = $401.50
- Defender Scanning: 56 × $10 = $560
- **Total: $961.50/month**

### Proposed Monthly Costs (10 workspaces)
- Storage Accounts: 12 total (1 core consolidated + 1 core processor + 10 workspace consolidated)
- Private Endpoints: 11 × $7.30 = $80.30
- Defender Scanning: 12 × $10 = $120
- **Total: $200.30/month**

### Savings
- **$761.20/month (79% reduction)**
- **$9,134.40/year**

As workspaces scale, savings increase:
- 50 workspaces: Current $2,881.50/month → Proposed $448.30/month = **$2,433.20/month savings (84%)**
- 100 workspaces: Current $5,681.50/month → Proposed $886.30/month = **$4,795.20/month savings (84%)**

## Security Considerations

### Network Isolation
- Consolidation maintains network isolation through private endpoints
- Same subnet restrictions apply (core uses `airlock_storage_subnet_id`, workspace uses `services_subnet_id`)
- Container-level access control through Azure RBAC and ABAC

### Access Control
- Current: Storage account-level RBAC
- Proposed: Storage account-level RBAC + container-level ABAC (optional)
- Service principals still require same permissions
- ABAC conditions can restrict access based on:
  - Container name prefix (stage)
  - Container metadata
  - Private endpoint used for access

### Data Integrity
- Maintain current copy-based approach for auditability
- Container deletion still occurs after successful copy
- Metadata tracks data lineage in `copied_from` field

### Malware Scanning
- Microsoft Defender for Storage works at storage account level
- Consolidated account still scanned
- EventGrid notifications still trigger on blob upload
- No change to scanning effectiveness

## Migration Strategy

### Phase 1: Infrastructure Preparation
1. Deploy consolidated storage accounts in parallel
2. Set up private endpoints
3. Configure EventGrid topics and subscriptions
4. Set up role assignments
5. Test infrastructure connectivity

### Phase 2: Code Updates
1. Update constants and configuration
2. Implement container naming with stage prefixes
3. Update blob operations functions
4. Add feature flag for consolidated mode
5. Unit and integration testing

### Phase 3: Pilot Migration
1. Enable consolidated mode for test workspace
2. Create new airlock requests using new infrastructure
3. Validate all stages of airlock flow
4. Monitor for issues

### Phase 4: Production Migration
1. Enable consolidated mode for all new requests
2. Existing requests continue using old infrastructure
3. Monitor and validate
4. After cutover period, clean up old infrastructure

### Phase 5: Decommission
1. Ensure no active requests on old infrastructure
2. Export any data needed for retention
3. Delete old storage accounts and private endpoints
4. Update documentation

## Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Data loss during migration | High | Parallel deployment, thorough testing, backups |
| Application bugs in new code | Medium | Feature flag, gradual rollout, extensive testing |
| Performance degradation | Low | Same storage tier, monitoring, load testing |
| EventGrid subscription issues | Medium | Parallel setup, validation testing |
| Role assignment errors | Medium | Validate permissions before cutover |
| Rollback complexity | Medium | Keep old infrastructure until fully validated |

## Testing Requirements

### Unit Tests
- Container name generation with prefixes
- Storage account name resolution
- Blob operations with new container names

### Integration Tests
- End-to-end airlock flow (import and export)
- Malware scanning triggers
- EventGrid notifications
- Role-based access control
- SAS token generation and validation

### Performance Tests
- Blob copy operations within same account
- Concurrent request handling
- Large file transfers

## Recommendations

1. **Implement Option B (Metadata-Based Stage Management)** for maximum efficiency and cost savings
2. **Benefits of metadata approach:**
   - Eliminates data copying overhead (90%+ faster stage transitions)
   - Reduces storage costs by 50% during transitions (no duplicate data)
   - Minimal code changes (container names stay as `request_id`)
   - Better auditability with complete history in single location
   - ABAC provides fine-grained access control
3. **Use feature flag** to enable gradual rollout
4. **Start with non-production environment** for validation
5. **Maintain backward compatibility** during migration period
6. **Document all changes** for operational teams
7. **Plan for 2-month migration window** (reduced from 3 months due to simpler approach)
8. **Enable blob versioning** on consolidated storage accounts for data protection
9. **Implement custom event publishing** for stage change notifications

## Next Steps

1. Review and approve updated design (metadata-based approach)
2. Create detailed implementation tasks
3. Estimate development effort (reduced due to simpler approach)
4. Plan sprint allocation
5. Begin Phase 1 (Infrastructure Preparation)

## Appendix A: Container Metadata-Based Stage Management

### Overview
Instead of copying data between storage accounts or containers, we use container metadata to track the current stage of an airlock request. This eliminates data copying overhead while maintaining security through ABAC conditions.

### Container Structure
- Container name: `{request_id}` (e.g., `abc-123-def-456`)
- Container metadata:
  ```json
  {
    "stage": "import-inprogress",
    "stage_history": "draft,submitted,inprogress",
    "created_at": "2024-01-15T10:30:00Z",
    "last_stage_change": "2024-01-15T11:45:00Z",
    "workspace_id": "ws123",
    "request_type": "import"
  }
  ```

### Stage Values
- `import-external` - Draft import requests (external drop zone)
- `import-inprogress` - Import requests being scanned/reviewed
- `import-approved` - Approved import requests (moved to workspace)
- `import-rejected` - Rejected import requests
- `import-blocked` - Import requests blocked by malware scan
- `export-internal` - Draft export requests (internal workspace)
- `export-inprogress` - Export requests being scanned/reviewed
- `export-approved` - Approved export requests (available externally)
- `export-rejected` - Rejected export requests
- `export-blocked` - Export requests blocked by malware scan

### Stage Transition Process

**Old Approach (Copying):**
```python
# 1. Copy blob from source account/container to destination account/container
copy_data(source_account, dest_account, request_id)
# 2. Wait for copy to complete
# 3. Delete source container
delete_container(source_account, request_id)
```

**New Approach (Metadata Update):**
```python
# 1. Update container metadata
update_container_metadata(
    account=consolidated_account,
    container=request_id,
    metadata={
        "stage": new_stage,
        "stage_history": f"{existing_history},{new_stage}",
        "last_stage_change": current_timestamp
    }
)
# No copying or deletion needed!
```

### ABAC Conditions for Access Control

**Example 1: Restrict API to only access external and in-progress stages**
```hcl
resource "azurerm_role_assignment" "api_limited_access" {
  scope                = azurerm_storage_account.sa_airlock_core.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.api_id.principal_id
  
  condition_version = "2.0"
  condition = <<-EOT
    (
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
      StringIn ('import-external', 'import-inprogress', 'export-approved')
    )
  EOT
}
```

**Example 2: Restrict workspace access to only approved import containers**
```hcl
resource "azurerm_role_assignment" "workspace_import_access" {
  scope                = azurerm_storage_account.sa_airlock_workspace.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.workspace_id.principal_id
  
  condition_version = "2.0"
  condition = <<-EOT
    (
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
      StringEquals 'import-approved'
      AND
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['workspace_id']
      StringEquals '${workspace_id}'
    )
  EOT
}
```

**Example 3: Airlock processor has full access**
```hcl
resource "azurerm_role_assignment" "airlock_processor_full_access" {
  scope                = azurerm_storage_account.sa_airlock_core.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.airlock_id.principal_id
  # No condition - full access to all containers regardless of stage
}
```

### Event Handling

**Challenge:** EventGrid blob created events trigger when blobs are created, not when metadata changes.

**Solution Options:**

1. **Custom Event Publishing:** Publish custom events when metadata changes
   ```python
   # After updating container metadata
   publish_event(
       topic="airlock-stage-changed",
       subject=f"container/{request_id}",
       event_type="AirlockStageChanged",
       data={
           "request_id": request_id,
           "old_stage": old_stage,
           "new_stage": new_stage,
           "timestamp": current_timestamp
       }
   )
   ```

2. **Azure Monitor Alerts:** Set up alerts on container metadata changes (Activity Log)

3. **Polling:** Periodically check container metadata (less efficient but simpler)

### Data Integrity and Audit Trail

**Metadata Versioning:**
```json
{
  "stage": "import-approved",
  "stage_history": "external,inprogress,approved",
  "stage_timestamps": {
    "external": "2024-01-15T10:00:00Z",
    "inprogress": "2024-01-15T10:30:00Z",
    "approved": "2024-01-15T11:45:00Z"
  },
  "stage_changed_by": {
    "external": "user@example.com",
    "inprogress": "system",
    "approved": "reviewer@example.com"
  },
  "scan_results": {
    "inprogress": "clean",
    "timestamp": "2024-01-15T10:35:00Z"
  }
}
```

**Immutability Options:**
1. Enable blob versioning on storage account
2. Use immutable blob storage with time-based retention
3. Copy metadata changes to append-only audit log
4. Use Azure Monitor/Log Analytics for change tracking

### Migration from Copy-Based to Metadata-Based

**Phase 1: Dual Mode Support**
- Add feature flag `USE_METADATA_STAGE_MANAGEMENT`
- Support both old (copy) and new (metadata) approaches
- New requests use metadata approach
- Existing requests complete using copy approach

**Phase 2: Gradual Rollout**
- Enable metadata approach for test workspaces
- Monitor and validate
- Expand to production workspaces

**Phase 3: Full Migration**
- All new requests use metadata approach
- Existing requests complete
- Remove copy-based code

### Performance Comparison

| Operation | Copy-Based | Metadata-Based | Improvement |
|-----------|------------|----------------|-------------|
| 1 GB file stage transition | ~30 seconds | ~1 second | 97% faster |
| 10 GB file stage transition | ~5 minutes | ~1 second | 99.7% faster |
| 100 GB file stage transition | ~45 minutes | ~1 second | 99.9% faster |
| Storage during transition | 2x file size | 1x file size | 50% reduction |
| API calls required | 3-5 | 1 | 70% reduction |

### Security Considerations

**Advantages:**
- ABAC provides fine-grained access control
- Metadata cannot be modified by users (only by service principals with write permissions)
- Access restrictions enforced at Azure platform level
- Audit trail preserved in single location

**Considerations:**
- Ensure metadata is protected from tampering
- Use managed identities for all metadata updates
- Monitor metadata changes through Azure Monitor
- Implement metadata validation before stage transitions
- Consider adding digital signatures to metadata for tamper detection

### Code Changes Summary

**Minimal Changes Required:**
1. Update `create_container()` to set initial stage metadata
2. Add `update_container_stage()` function to update metadata
3. Replace `copy_data()` calls with `update_container_stage()` calls
4. Remove `delete_container()` calls (containers persist)
5. Update access control to use ABAC conditions
6. Update event publishing for stage changes

**Example Implementation:**
```python
def update_container_stage(account_name: str, request_id: str, 
                          new_stage: str, user: str):
    """Update container stage metadata instead of copying data."""
    container_client = get_container_client(account_name, request_id)
    
    # Get current metadata
    properties = container_client.get_container_properties()
    metadata = properties.metadata
    
    # Update metadata
    old_stage = metadata.get('stage', 'unknown')
    metadata['stage'] = new_stage
    metadata['stage_history'] = f"{metadata.get('stage_history', '')},{new_stage}"
    metadata['last_stage_change'] = datetime.now(UTC).isoformat()
    metadata['last_changed_by'] = user
    
    # Set updated metadata
    container_client.set_container_metadata(metadata)
    
    # Publish custom event
    publish_stage_change_event(request_id, old_stage, new_stage)
    
    logging.info(f"Updated container {request_id} from {old_stage} to {new_stage}")
```

## Appendix B: Container Naming Convention

### Metadata-Based Approach (Recommended)
- Container name: `{request_id}` (e.g., `abc-123-def-456`)
- Stage tracked in metadata: `stage=import-external`
- Storage account: Consolidated account
- Example: Container `abc-123-def` with metadata `stage=import-inprogress` in storage account `stalairlockmytre`

**Advantages:**
- Minimal code changes (container naming stays the same)
- Stage changes via metadata update (no data copying)
- Single source of truth
- Complete audit trail in metadata

### Legacy Approach (For Reference)
- Container name: `{request_id}` (e.g., `abc-123-def`)
- Storage account varies by stage
- Example: Container `abc-123-def` in storage account `stalimexmytre`

**Issues:**
- Requires data copying between storage accounts
- Higher costs and complexity
- Slower stage transitions

## Appendix C: ABAC Condition Examples

### Metadata-Based Access Control

### Restrict access to specific stage only
```hcl
condition_version = "2.0"
condition = <<-EOT
  (
    !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'})
    OR
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] StringEquals 'import-external'
  )
EOT
```

### Allow access to multiple stages
```hcl
condition_version = "2.0"
condition = <<-EOT
  (
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
    StringIn ('import-external', 'import-inprogress', 'export-approved')
  )
EOT
```

### Restrict by workspace AND stage
```hcl
condition_version = "2.0"
condition = <<-EOT
  (
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] StringEquals 'import-approved'
    AND
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['workspace_id'] StringEquals 'ws123'
  )
EOT
```

### Restrict access based on private endpoint AND stage
```hcl
condition_version = "2.0"
condition = <<-EOT
  (
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] StringStartsWith 'export-'
    AND
    @Request[Microsoft.Network/privateEndpoints] StringEquals '/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Network/privateEndpoints/pe-workspace-services'
  )
EOT
```

### Allow write access only to draft stages
```hcl
condition_version = "2.0"
condition = <<-EOT
  (
    !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'})
    OR
    (
      @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] StringIn ('import-external', 'export-internal')
    )
  )
EOT
```

### Block access to blocked/rejected stages
```hcl
condition_version = "2.0"
condition = <<-EOT
  (
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
    StringNotIn ('import-blocked', 'import-rejected', 'export-blocked', 'export-rejected')
  )
EOT
```
