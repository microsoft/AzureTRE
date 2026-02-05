# Analysis: Do We Need Separate Workspace Airlock Storage Accounts?

## Question

Can we consolidate ALL airlock storage into **1 single storage account** for the entire TRE instead of 1 per workspace?

## Short Answer

**We COULD technically, but SHOULD NOT** due to workspace isolation requirements, operational complexity, and cost/benefit analysis.

## Technical Feasibility: YES with ABAC

### How It Would Work

**1 Global Storage Account:**
- Name: `stalairlock{tre_id}`
- Contains: ALL stages for ALL workspaces
- Container naming: `{workspace_id}-{request_id}` (add workspace prefix)
- Metadata: `{"workspace_id": "ws123", "stage": "export-internal"}`

**Private Endpoints (10 workspaces):**
- PE #1: App Gateway (public access routing)
- PE #2: Airlock processor
- PE #3: Import review workspace  
- PE #4-13: One per workspace (10 PEs)

**Total: 13 PEs** (same as workspace-per-account approach)

**ABAC Conditions:**
```hcl
# Workspace A researcher access
condition = <<-EOT
  (
    @Environment[Microsoft.Network/privateEndpoints] StringEqualsIgnoreCase 
      '${azurerm_private_endpoint.workspace_a_pe.id}'
    AND
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['workspace_id'] 
      StringEquals 'ws-a'
    AND
    @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage'] 
      StringIn ('export-internal', 'import-approved')
  )
EOT
```

## Why We SHOULD NOT Do This

### 1. Workspace Isolation is a Core Security Principle

**From docs:** "Workspaces represent a security boundary"

**With shared storage:**
- ❌ All workspace data in same storage account
- ❌ Blast radius increases (one misconfiguration affects all workspaces)
- ❌ Harder to audit per-workspace access
- ❌ Compliance concerns (data segregation)

**With separate storage:**
- ✅ Strong isolation boundary
- ✅ Limited blast radius
- ✅ Clear audit trail per workspace
- ✅ Meets compliance requirements

### 2. Operational Complexity

**With shared storage:**
- ❌ Complex ABAC conditions for every workspace
- ❌ ABAC must filter by workspace_id + PE + stage
- ❌ Adding workspace = updating ABAC on shared storage
- ❌ Removing workspace = ensuring no data remains
- ❌ Debugging access issues across workspaces is harder

**With separate storage:**
- ✅ Simple ABAC (only by stage, not workspace)
- ✅ Adding workspace = create new storage account
- ✅ Removing workspace = delete storage account (clean)
- ✅ Clear separation of concerns

### 3. Cost/Benefit Analysis

**Savings with 1 global account:**
- Remove 10 workspace storage accounts
- Save: 10 × $10 Defender = $100/month
- But: Still need 10 workspace PEs (no PE savings)
- Net additional savings: **$100/month**

**Costs of 1 global account:**
- Increased operational complexity
- Higher security risk (shared boundary)
- Harder troubleshooting
- Compliance concerns

**Conclusion:** $100/month is NOT worth the operational and security costs!

### 4. Workspace Lifecycle Management

**With shared storage:**
- Workspace deletion requires:
  1. Find all containers with workspace_id
  2. Delete containers
  3. Update ABAC conditions
  4. Risk of orphaned data
  5. No clear "workspace is gone" signal

**With separate storage:**
- Workspace deletion:
  1. Delete storage account
  2. Done!
  3. Clean, atomic operation

### 5. Cost Allocation and Billing

**With shared storage:**
- ❌ Cannot see per-workspace storage costs directly
- ❌ Need custom tagging and cost analysis
- ❌ Harder to charge back to research groups

**With separate storage:**
- ✅ Azure Cost Management shows per-workspace costs automatically
- ✅ Easy chargeback to research groups
- ✅ Clear budget tracking

### 6. Scale Considerations

**At 100 workspaces:**

**With shared storage:**
- 1 storage account with 100 PEs
- Extremely complex ABAC with 100+ conditions
- Management nightmare
- Single point of failure

**With per-workspace storage:**
- 100 storage accounts with 100 PEs
- Same number of PEs (no disadvantage)
- Simple, repeatable pattern
- Distributed risk

### 7. Private Endpoint Limits

**Azure Limits:**
- Max PEs per storage account: **No documented hard limit**, but...
- Performance degrades with many PEs
- Complex routing tables
- DNS complexity

**With 100 workspaces:**
- Shared: 1 account with 102+ PEs (app gateway + processor + review + 100 workspaces)
- Separate: 1 core account with 3 PEs, 100 workspace accounts with 1 PE each
- **Separate is more scalable**

## Recommendation: Keep 1 Storage Account Per Workspace

### Final Architecture

**Core: 1 Storage Account**
- `stalairlock{tre_id}` - All 5 core stages
- 3 PEs: App Gateway, Processor, Import Review
- Serves all workspaces for core operations

**Workspace: 1 Storage Account Each**
- `stalairlockws{ws_id}` - All 5 workspace stages
- 1 PE: Workspace services subnet
- Isolates workspace data

**For 10 workspaces:**
- **11 storage accounts** (was 56) = **80% reduction**
- **13 private endpoints** (was 55) = **76% reduction**
- **$756.60/month savings** = $9,079/year

### Benefits of This Approach

**Security:**
- ✅ Maximum consolidation (80% reduction)
- ✅ Workspace isolation maintained
- ✅ Simple ABAC conditions (no cross-workspace filtering)
- ✅ Limited blast radius
- ✅ Compliance-friendly

**Operations:**
- ✅ Clear workspace boundaries
- ✅ Easy workspace lifecycle (create/delete)
- ✅ Simple troubleshooting
- ✅ Scalable to 100+ workspaces

**Cost:**
- ✅ Massive savings vs. current (80% reduction)
- ✅ Minimal additional cost vs. 1 global account (~$100/month)
- ✅ Worth it for operational simplicity

**Monitoring:**
- ✅ Per-workspace cost tracking
- ✅ Per-workspace usage metrics
- ✅ Clear audit boundaries

## Comparison Table

| Aspect | 1 Global Account | 1 Per Workspace | Winner |
|--------|------------------|-----------------|--------|
| Storage accounts (10 WS) | 1 | 11 | Global |
| Private endpoints | 13 | 13 | Tie |
| Monthly cost | $194.90 | $204.90 | Global (+$10) |
| Workspace isolation | Complex ABAC | Natural | Per-WS |
| ABAC complexity | Very high | Simple | Per-WS |
| Lifecycle management | Complex | Simple | Per-WS |
| Cost tracking | Manual | Automatic | Per-WS |
| Scalability | Poor (100+ PEs) | Good | Per-WS |
| Security risk | Higher | Lower | Per-WS |
| Compliance | Harder | Easier | Per-WS |

**Winner: 1 Per Workspace** (operational benefits far outweigh $10/month extra cost)

## Conclusion

**Keep the current design:**
- 1 core storage account (all core stages)
- 1 storage account per workspace (all workspace stages)

This provides:
- 80% cost reduction
- Strong workspace isolation
- Simple operations
- Clear compliance boundaries
- Scalable architecture

The additional ~$100/month to keep workspace accounts separate is a worthwhile investment for security, simplicity, and maintainability.
