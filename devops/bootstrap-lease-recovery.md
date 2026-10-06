# Bootstrap lease recovery and CI exclusion

Automatic recovery only applies to an empty, infinitely leased `bootstrap.tfstate`
without a Terraform lock owner, in a verified PR CI backend. It never unlocks
populated state. See [issue #5115](https://github.com/microsoft/AzureTRE/issues/5115).

## Ownership and exclusion

The existing `deploy-<ci_git_ref>` GitHub concurrency group protects the complete
deployment, including bootstrap, Terraform and E2E work. Explicit destruction and
scheduled cleanup use the same group. Groups do not cancel a running owner.
GitHub's default single-pending queue remains unchanged: a newer waiting operation
can replace an older waiting operation, but cannot interrupt the active owner.

The key deliberately covers all clouds, subscriptions and regions for one
reference. Explicit destruction searches previous regional environments by tag.
Narrowing only the deployment key to an account or regional ID would leave those
cross-region deletions outside the same exclusion mechanism.

Recovery binds the reference to the expected legacy or regional account name,
subscription, container and management resource group tag. GitHub's concurrency
API must positively identify this run as the sole active group owner. When it
reports a reusable-workflow job, recovery also verifies the management job and
run attempt. Missing, duplicate, incomplete or inconsistent responses refuse
recovery. Queued successors remain harmless because GitHub retains the lock
until the deployment finishes.

The full group endpoint returns the complete queue. The implementation checks
its count and member identities. The filtered `ahead_of_run` and `ahead_of_job`
queries returned HTTP 422 for an active reusable workflow during read-only
verification on 6 October 2026, although the full endpoint identified its owner.
They are therefore not used. See the
[GitHub concurrency API](https://docs.github.com/en/rest/actions/concurrency-groups)
and [concurrency behaviour](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

## Writer audit

| Entry point | Backend selection | Exclusion |
| --- | --- | --- |
| PR comment deployment | Validated PR reference and regional environment ID | Reusable workflow holds `deploy-${{ inputs.ciGitRef }}` throughout deployment |
| Branch deployment | Branch reference and regional environment ID | Same reusable workflow group |
| Main deployment | Configured main environment | Same reusable workflow, normally `deploy-refs/heads/main` |
| Explicit PR destruction | Current resource groups tagged with the selected PR reference | `destroy_pr_env` holds the matching reference group and waits for deletion |
| Explicit branch destruction | Current resource groups tagged with the selected branch reference | `destroy_branch_env` holds the matching reference group and waits for deletion |
| Scheduled or dispatched cleanup | Read-only Azure tag discovery, then fresh selection inside each matrix job | Each job holds its reference group, verifies the actual job owner and rechecks core/management tags before mutation |
| Main workspace cleanup | Configured main TRE workspace prefix | Separate matrix entry holding `deploy-refs/heads/main` |
| Disposable cleanup validation | Synthetic reference containing run ID and attempt | Dedicated reference group, with the existing fixture ownership and empty-resource allow-list |

The planner discovers references, not approved deletion actions. A queued cleanup
job reevaluates PR status, branch activity, resource groups and ownership after
acquiring its lock. Different regions for the same reference share one job.
Deletion is synchronous so the job retains exclusion until Azure returns.
Unscoped invocations of the cleanup script refuse to run.

The recovery helper checks immutable workflow source blob hashes against the
checkout before accepting another known writer or unrelated repository workflow.
It also checks that the current caller and reusable deployment use the same
source commit and the updated cleanup wiring. It never derives a comment run's
target from `head_branch`, `pull_requests` or a display title. The GitHub-managed
Copilot review, GitHub-managed CodeQL, and GitHub Pages deployment are identified
by their exact dynamic workflow paths and event.
Unknown workflows, changed definitions, old cleanup wiring and unavailable
ownership evidence refuse recovery. Certificate renewal and CLI publishing are
conservatively treated as unknown because their configured targets are not
established by this recovery contract.

The workflow activity scan detects unknown or legacy writers. It is not the
lock. A new supported writer arriving after the final scan still has to acquire
the reference group before it can write or delete. The conditional blob break
separately protects content and metadata changes. Lease changes alone do not
change the blob ETag and are not ownership evidence.

## Rollout and validation

This is a cooperative CI protocol. Privileged manual Azure operations and old or
modified workflows that bypass the group must not run against a recovering
backend. Drain legacy cleanup runs before enabling the new workflow definitions.
Do not dispatch or rerun old cleanup definitions afterwards. An activity snapshot
cannot prevent a privileged operator from starting an unsupported writer later.

A `/test` comment reads workflow definitions from the default branch. Checking out
this script from a PR does not activate the new cleanup contract. Recovery
intentionally refuses when the executing workflow source lacks that contract.
Use a trusted branch containing all changed wiring for cleanup validation.
The recovery helper remains restricted to PR comment deployments. A full
pre-merge lease test needs trusted comment-workflow wiring in a disposable test
repository or a dedicated validation harness. Branch deployment alone does not
enable this helper.

Local tests cover unrelated workflows, verified writer definitions, queued
successors arriving during recovery, lost ownership, unknown writers, pagination,
API errors, stale attempts, cleanup scope and synchronous destruction. They also
run the real shell scripts with mocked services to check lease preservation and
restoration of storage network access after failures and cancellation. These
tests do not demonstrate GitHub scheduling or a live Azure lease break.

Before marking the PR ready:

1. Run the changed workflows from a trusted branch against disposable resources.
2. Overlap unrelated lint, Copilot, GitHub-managed CodeQL, and GitHub Pages work
   with an eligible empty bootstrap lease.
3. Queue deployment and destruction for the same reference during recovery.
4. Confirm that the new writer cannot start until the current deployment releases its group.
5. Repeat with scheduled cleanup, a separate reference and a failed or cancelled bootstrap.
6. Record the commit, workflow source, run IDs, blob integrity and restored network settings.
7. Confirm that disposable resources have been removed.

A terminated runner cannot guarantee completion of an Azure operation already
accepted by the service. If deletion or access restoration is interrupted, verify
its completion before reusing the environment.
