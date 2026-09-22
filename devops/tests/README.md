# CI cleanup validation

Run the local regression tests from the repository root:

```bash
python3 -m unittest discover -s devops/tests -p 'test_*.py' -v
```

These tests use mocked Azure and GitHub services. They cover bootstrap tags,
cleanup decisions, the real destroy helper, and the live validation guard.

## Validate with GitHub Actions

The **Clean Validation Environments** workflow has two manual modes:

- `validate` (default) creates two disposable empty groups and tests this commit.
- `cleanup` runs the normal subscription cleanup sweep.

Scheduled runs continue to use the normal cleanup sweep.

To validate a trusted branch, run:

```bash
gh workflow run clean_validation_envs.yml --repo microsoft/AzureTRE \
  --ref YOUR_BRANCH -f mode=validate -f validation_location=westeurope
```

The branch must exist in the target repository. Before merge, a maintainer can
create a temporary branch at the reviewed PR commit, then remove it after testing.
The workflow uses the existing `CICD` environment and its Azure OIDC credentials.
The identity needs resource-group creation, reading, tagging and deletion permissions.
Repository rules and environment approval requirements still apply.

Run validation when other workflows are idle. Cleanup retains its active-workflow
check. If that check skips cleanup, validation reports an incomplete result and
removes the fixtures. Run validation again when the repository is idle.

## Coverage and limits

The validation executes the original bootstrap and cleanup scripts through an
Azure CLI guard. It checks these behaviours:

- New CI groups receive their ownership reference before an injected storage failure.
- Reruns update that reference and preserve unrelated tags.
- Non-CI runs preserve tags and do not add a CI reference.
- Cleanup selects the tagged orphan and deletes it after a guarded preview.
- A similarly named neighbour survives cleanup.
- All fixtures are absent after the final cleanup step.
- Non-fixture resource-group names and tags remain unchanged.

The guard permits mutations only on the two groups generated for this run.
It checks the Azure identity, exact group identity, ownership marker, empty contents
and absence of locks before deletion. It blocks storage creation and other Azure
commands. Discovery uses Azure responses filtered to the fixtures. The main-workspace
sweep is excluded. This validates management-orphan cleanup, not a full TRE teardown.

The job summary and artifact contain sanitised assertions and the tested commit.
They exclude raw Azure output, account details and the private fixture state.
An incomplete test or failed fixture cleanup cannot produce a passing summary.

The final cleanup step runs after a failure or cancellation while the runner remains
available. If the runner is lost, inspect groups tagged `cleanup_validation_run`
with the workflow run ID and attempt prefix. If available, use the exact marker
from the summary. Verify ownership and contents before manual deletion.
