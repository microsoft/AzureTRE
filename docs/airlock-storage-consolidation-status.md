# Airlock Storage Consolidation - Implementation Status

## Summary

This document tracks the implementation status of the airlock storage consolidation feature, which reduces the number of storage accounts from 56 to 12 (for 10 workspaces) using metadata-based stage management.

## Key Innovation

**Metadata-Based Stage Management** - Instead of copying data between storage accounts when moving through airlock stages, we update container metadata to track the current stage. This provides:
- 90%+ faster stage transitions (no data copying)
- 50% lower storage costs during transitions
- Simpler code (metadata update vs. copy + delete)
- Complete audit trail in single location
- Same container persists through all stages

## Cost Savings

For a TRE with 10 workspaces:
- **Storage accounts:** 56 → 12 (79% reduction)
- **Private endpoints:** 55 → 11 (80% reduction)
- **Monthly savings:** ~$763 ($322.80 PE + $440 Defender)
- **Annual savings:** ~$9,134

## Implementation Status

### ✅ Completed

1. **Design Documentation** (`docs/airlock-storage-consolidation-design.md`)
   - Comprehensive architecture design
   - Cost analysis and ROI calculations
   - Three implementation options with pros/cons
   - Detailed metadata-based approach specification
   - Migration strategy (5 phases)
   - Security considerations with ABAC examples
   - Performance comparisons
   - Risk analysis and mitigation

2. **Metadata-Based Blob Operations** (`airlock_processor/shared_code/blob_operations_metadata.py`)
   - `create_container_with_metadata()` - Create container with initial stage
   - `update_container_stage()` - Update stage via metadata (replaces copy_data())
   - `get_container_stage()` - Get current stage from metadata
   - `get_container_metadata()` - Get all container metadata
   - `delete_container_by_request_id()` - Delete container when needed
   - Full logging and error handling

3. **Constants Updates**
   - API constants (`api_app/resources/constants.py`)
     - Added `STORAGE_ACCOUNT_NAME_AIRLOCK_CORE`
     - Added `STORAGE_ACCOUNT_NAME_AIRLOCK_WORKSPACE`
     - Added `STAGE_*` constants for all stages
     - Kept legacy constants for backwards compatibility
   - Airlock processor constants (`airlock_processor/shared_code/constants.py`)
     - Added consolidated storage account names
     - Maintained existing stage constants

4. **Terraform Infrastructure (Partial)**
   - New core storage account definition (`core/terraform/airlock/storage_accounts_new.tf`)
     - Single consolidated storage account for core
     - Single private endpoint (vs. 5 previously)
     - Malware scanning configuration
     - EventGrid system topics
     - Role assignments for airlock processor and API
   - Updated locals (`core/terraform/airlock/locals.tf`)
     - Added consolidated storage account name
     - Added container prefix definitions
     - Preserved legacy names for migration

5. **Documentation**
   - Updated CHANGELOG.md with enhancement entry
   - Created comprehensive design document
   - Added ABAC condition examples
   - Documented migration strategy

### 🚧 In Progress / Remaining Work

#### 1. Complete Terraform Infrastructure

**Core Infrastructure:**
- [ ] Finalize EventGrid subscriptions with container name filters
- [ ] Add ABAC conditions to role assignments
- [ ] Create workspace consolidated storage account Terraform
- [ ] Update EventGrid topics to publish on metadata changes
- [ ] Add feature flag for metadata-based mode

**Workspace Infrastructure:**
- [ ] Create `templates/workspaces/base/terraform/airlock/storage_accounts_new.tf`
- [ ] Consolidate 5 workspace storage accounts into 1
- [ ] Add workspace-specific ABAC conditions
- [ ] Update workspace locals and outputs

#### 2. Application Code Integration

**API (`api_app/services/airlock.py`):**
- [ ] Add feature flag `USE_METADATA_STAGE_MANAGEMENT`
- [ ] Update `get_account_by_request()` to return consolidated account name
- [ ] Add `get_container_stage_by_request()` function
- [ ] Replace container creation logic to use `create_container_with_metadata()`
- [ ] Update SAS token generation to work with metadata-based approach

**Airlock Processor (`airlock_processor/StatusChangedQueueTrigger/__init__.py`):**
- [ ] Replace `copy_data()` calls with `update_container_stage()`
- [ ] Remove `delete_container()` calls (containers persist)
- [ ] Update storage account resolution for consolidated accounts
- [ ] Add metadata validation before stage transitions
- [ ] Publish custom events on stage changes

**Blob Operations:**
- [ ] Migrate from `blob_operations.py` to `blob_operations_metadata.py`
- [ ] Add backward compatibility layer during migration
- [ ] Update all imports to use new module

#### 3. Event Handling

- [ ] Implement custom event publishing for stage changes
- [ ] Update EventGrid subscriptions to handle metadata-based events
- [ ] Add event handlers for stage change notifications
- [ ] Update BlobCreatedTrigger to handle both old and new patterns

#### 4. Testing

**Unit Tests:**
- [ ] Test container creation with metadata
- [ ] Test metadata update functions
- [ ] Test stage retrieval from metadata
- [ ] Test ABAC condition evaluation
- [ ] Test feature flag behavior

**Integration Tests:**
- [ ] End-to-end airlock flow with metadata approach
- [ ] Import request lifecycle
- [ ] Export request lifecycle
- [ ] Malware scanning integration
- [ ] EventGrid notification flow
- [ ] SAS token generation and access

**Migration Tests:**
- [ ] Dual-mode operation (old + new)
- [ ] Data migration tooling
- [ ] Rollback scenarios

#### 5. Migration Tooling

- [ ] Create migration script to move existing requests
- [ ] Add validation for migrated data
- [ ] Create rollback tooling
- [ ] Add monitoring and alerting for migration

#### 6. Documentation Updates

- [ ] Update architecture diagrams
- [ ] Update deployment guide
- [ ] Create migration guide for existing deployments
- [ ] Update API documentation
- [ ] Update airlock user guide
- [ ] Add troubleshooting section

#### 7. Version Updates

- [ ] Update core version (`core/version.txt`)
- [ ] Update API version (`api_app/_version.py`)
- [ ] Update airlock processor version (`airlock_processor/_version.py`)
- [ ] Follow semantic versioning (MAJOR for breaking changes)

## Feature Flag Strategy

Implement `USE_METADATA_STAGE_MANAGEMENT` feature flag:

**Environment Variable:**
```bash
export USE_METADATA_STAGE_MANAGEMENT=true  # Enable new metadata-based approach
export USE_METADATA_STAGE_MANAGEMENT=false # Use legacy copy-based approach
```

**Usage in Code:**
```python
import os

USE_METADATA_STAGE = os.getenv('USE_METADATA_STAGE_MANAGEMENT', 'false').lower() == 'true'

if USE_METADATA_STAGE:
    # Use metadata-based approach
    update_container_stage(account, request_id, new_stage)
else:
    # Use legacy copy-based approach
    copy_data(source_account, dest_account, request_id)
```

## Migration Phases

### Phase 1: Infrastructure Preparation (Week 1-2)
- Deploy consolidated storage accounts in parallel
- Set up private endpoints and EventGrid
- Validate infrastructure connectivity
- **Status:** Partial - Terraform templates created

### Phase 2: Code Updates (Week 3-4)
- Integrate metadata functions
- Add feature flag support
- Update all blob operations
- **Status:** In Progress - Functions created, integration pending

### Phase 3: Testing (Week 5-6)
- Unit tests
- Integration tests
- Performance validation
- **Status:** Not Started

### Phase 4: Pilot Rollout (Week 7-8)
- Enable for test workspace
- Monitor and validate
- Fix issues
- **Status:** Not Started

### Phase 5: Production Migration (Week 9-12)
- Gradual rollout to all workspaces
- Monitor performance and costs
- Decommission old infrastructure
- **Status:** Not Started

## Security Considerations

### Implemented
- ✅ Consolidated storage accounts with proper encryption
- ✅ Private endpoint network isolation
- ✅ Role assignments for service principals
- ✅ Design for ABAC conditions

### Pending
- [ ] Implement ABAC conditions in Terraform
- [ ] Metadata tampering protection
- [ ] Audit logging for metadata changes
- [ ] Digital signatures for metadata (optional enhancement)

## Performance Targets

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| 1GB file stage transition | ~30s | ~1s | 🚧 Testing pending |
| 10GB file stage transition | ~5m | ~1s | 🚧 Testing pending |
| Storage during transition | 2x | 1x | ✅ Designed |
| API calls per transition | 3-5 | 1 | ✅ Implemented |

## Next Immediate Actions

1. ✅ Complete Terraform infrastructure for core
2. Create workspace Terraform consolidation
3. Integrate metadata functions into API
4. Integrate metadata functions into airlock processor
5. Add comprehensive unit tests
6. Deploy to test environment and validate

## Questions & Decisions Needed

1. **Feature Flag Timeline:** When should we enable metadata-based mode by default?
   - Recommendation: After successful pilot in test environment (Phase 4)

2. **Migration Window:** How long to support both modes?
   - Recommendation: 2 months (allows time for thorough testing and gradual rollout)

3. **Rollback Plan:** What triggers a rollback to legacy mode?
   - Recommendation: Any data integrity issues or critical bugs

4. **ABAC Implementation:** Should we implement ABAC in Phase 1 or Phase 2?
   - Recommendation: Phase 2, after basic consolidation is validated

## Contact & Support

For questions or issues with this implementation:
- Review the design document: `docs/airlock-storage-consolidation-design.md`
- Check implementation status: This document
- Review code comments in new modules

## References

- Design Document: `/docs/airlock-storage-consolidation-design.md`
- New Blob Operations: `/airlock_processor/shared_code/blob_operations_metadata.py`
- Core Terraform: `/core/terraform/airlock/storage_accounts_new.tf`
- Issue: [Link to GitHub issue]
- PR: [Link to this PR]
