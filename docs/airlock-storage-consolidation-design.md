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

### New Data Flow
1. Container created with `{stage}-{request_id}` as name in consolidated storage account
2. Data uploaded to container
3. On status change, data **copied** to new container `{new_stage}-{request_id}` in **same** storage account
4. Source container deleted after successful copy

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

### Option B: Partial Consolidation with Metadata

**Pros:**
- Minimal application code changes
- Can use ABAC for future enhancements
- Container names remain as `request_id`

**Cons:**
- More complex container metadata management
- Still requires infrastructure changes
- ABAC conditions add complexity

**Changes Required:**
1. Keep `request_id` as container name
2. Add metadata `stage={stage_name}` to containers
3. Update stage by changing metadata instead of copying
4. Use ABAC conditions to restrict access based on metadata

**Note:** This approach changes the fundamental data flow (update vs. copy) and may have security/audit implications.

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

1. **Implement Option A (Full Consolidation)** for maximum cost savings
2. **Use feature flag** to enable gradual rollout
3. **Start with non-production environment** for validation
4. **Maintain backward compatibility** during migration period
5. **Document all changes** for operational teams
6. **Plan for 3-month migration window** to ensure stability

## Next Steps

1. Review and approve design
2. Create detailed implementation tasks
3. Estimate development effort
4. Plan sprint allocation
5. Begin Phase 1 (Infrastructure Preparation)

## Appendix A: Container Naming Convention

### Current
- Container name: `{request_id}` (e.g., `abc-123-def`)
- Storage account varies by stage

### Proposed
- Container name: `{stage}-{request_id}` (e.g., `import-external-abc-123-def`)
- Storage account: Consolidated account for all stages

### Stage Prefixes
- `import-external` - Draft import requests
- `import-inprogress` - Import requests being scanned/reviewed
- `import-approved` - Approved import requests  
- `import-rejected` - Rejected import requests
- `import-blocked` - Import requests blocked by malware scan
- `export-internal` - Draft export requests
- `export-inprogress` - Export requests being scanned/reviewed
- `export-approved` - Approved export requests
- `export-rejected` - Rejected export requests
- `export-blocked` - Export requests blocked by malware scan

## Appendix B: ABAC Condition Examples

### Restrict access to import-external containers only
```hcl
condition = <<-EOT
  (
    !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'})
    OR
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringStartsWith 'import-external-'
  )
EOT
```

### Restrict access based on private endpoint
```hcl
condition = <<-EOT
  (
    @Request[Microsoft.Network/privateEndpoints] StringEquals '/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/privateEndpoints/{pe_name}'
  )
EOT
```

### Combined: Container prefix AND private endpoint
```hcl
condition = <<-EOT
  (
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringStartsWith 'import-external-'
    AND
    @Request[Microsoft.Network/privateEndpoints] StringEquals '/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/privateEndpoints/{pe_name}'
  )
EOT
```
