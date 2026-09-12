---
name: pr-tester
description: Validate an AzureTRE pull request locally and, when explicitly authorized, against a specified Azure TRE environment.
user-invocable: true
argument-hint: PR link, PR number, branch name, or commit SHA
---

# AzureTRE PR Tester

Use this workflow for requests such as “test this PR”, “validate PR 123”, or
“verify this branch”. Validate the exact PR revision without changing its source
logic and finish with an evidence-based verdict.

## Authorization and safety

A request to test a PR does not by itself authorize live Azure changes. Before
any external side effect, confirm the target environment, subscription/resource
scope, authorization, and cleanup expectations. Ask for approval immediately
before the first operation that changes the environment unless the user has
explicitly authorized that specific operation and environment.

External side effects include:

- pushing images or publishing/registering bundles;
- deploying or changing Azure/Terraform resources;
- creating, deleting, or modifying workspaces or test data;
- running tests against a shared or production-like environment;
- egress, isolation, or other security probes.

Use synthetic data, bounded test identities, and known test workspaces for
authorized security checks. Never perform uncontrolled scanning, exfiltration,
or access to unrelated workspaces.

Do not:

- modify application logic, tests, API contracts, or security policy to make the
  PR pass;
- merge or rebase the PR onto `main` unless explicitly requested;
- discard existing working-tree changes;
- commit, push, amend, force-push, or modify the PR;
- report PASS without concrete test, deployment, or functional evidence.

Environment fixes must be minimal, documented, independently applicable to the
baseline, and reported separately from PR results. Revert temporary changes when
safe to do so.

## Workflow

### 1. Resolve the target

Resolve a PR link, number, branch, or commit to the exact PR head SHA. Fetch
metadata and inspect the title, description, changed files, and relevant review
context. Record the branch and SHA. Do not assume that the currently checked-out
branch is the target.

Prefer an isolated worktree. If the current worktree is dirty, preserve it and
stop to resolve the conflict or use a separate worktree; never use a forced
checkout or destructive cleanup.

### 2. Plan and scope

Create a short todo list covering:

1. target branch and SHA;
2. changed components;
3. local checks;
4. external operations, if authorized;
5. functional and security checks;
6. cleanup and reporting.

Determine affected components from the diff. Typical areas are `api_app`,
`resource_processor`, `airlock_processor`, `ui`, `core/terraform`, and
`templates`. Do not build, push, register, or redeploy unaffected components.

Write a 3–6 bullet test plan stating the PR goal, checks, expected results, and
any failure-mode or security checks required by the changed surface.

### 3. Run local checks first

Run focused unit tests before any deployment. Start with the changed test file
or module and expand to the relevant package suite. Also run applicable lint,
type, formatting, bundle, or Terraform validation checks.

Useful starting points include:

```bash
cd api_app && python -m pytest <relevant-test> -q
cd resource_processor && python -m pytest <relevant-test> -q
cd airlock_processor && python -m pytest <relevant-test> -q
terraform fmt -check -recursive
make lint-docs
```

Use `make lint` for repository-wide linting when Docker and the required tools
are available. Stop and report a local test failure before attempting a live
deployment unless the user explicitly asks for deployment despite the failure.

### 4. Build and deploy only with authorization

If live validation is authorized, build only images affected by the diff. Use
scoped Make targets rather than `make images`. Deploy only the affected API,
UI, processor, core, or bundle components.

Before applying Terraform or running deployment targets, inspect the plan and
watch for replacement or destruction of shared infrastructure. Pause if the
operation exceeds the authorized scope or would be destructive.

The repository's E2E Make targets may or may not be usable in the current
environment. Determine their prerequisites rather than assuming they run locally
or assuming they are unavailable. If equivalent manual checks are used, report
that full E2E coverage was not obtained.

### 5. Verify the deployment is the PR

Before functional validation, confirm that the running artifacts came from the
exact PR revision:

- compare image tags or digests with the just-built artifacts;
- check API/UI-reported versions where available;
- compare bundle versions and `porter.yaml` metadata;
- confirm the deployed component is not a stale image or registration.

If the deployed version cannot be established, do not claim live validation of
the PR. Report `BLOCKED` or `PARTIAL`.

### 6. Functional and security validation

Exercise the changed behavior against the authorized environment and assert
responses, state, and cleanup. Test both the stated happy path and relevant
failure modes, including invalid or missing input, duplicate/concurrent
operations, timeouts/retries, partial failure, rollback, and name collisions.

For API changes, where applicable, test:

- missing, expired, and malformed credentials;
- wrong-role and wrong-workspace access;
- core-token versus workspace-token boundaries;
- ownership and IDOR access to resource identifiers;
- validation of new or oversized fields.

For Airlock, storage, networking, firewall, private endpoint/DNS, or workspace
isolation changes, use synthetic fixtures to verify that import/export review
flows, blob access, SAS/role scope, egress, DNS, and workspace boundaries remain
intact. Treat a confirmed boundary bypass as a blocking finding.

### 7. Report

Always state the checked-out branch, exact SHA, target environment, and whether
external operations were authorized. Use this format:

```text
PR: <link/number> — <title>
Branch: <branch>
Commit: <exact SHA>
Environment: <local only or target TRE/subscription/resource scope>

| Stage | Result | Detail |
|---|---|---|
| Test plan | PASS / – | checks defined |
| Unit tests | PASS / FAIL / – | counts and command |
| Lint/build/validation | PASS / FAIL / – | command and result |
| Images/artifacts | PASS / FAIL / – | affected artifacts and versions |
| Deploy | PASS / FAIL / – | components and notable changes |
| Deployed = PR | PASS / FAIL / – | versions/digests |
| Functional | PASS / FAIL / PARTIAL / – | checks and evidence |
| Data isolation | PASS / FAIL / PARTIAL / – | only when applicable |
| API security | PASS / FAIL / PARTIAL / – | only when applicable |
| Cleanup | PASS / FAIL / – | actions or pending work |

Verdict: PASS / FAIL / PARTIAL / BLOCKED — <one-line justification>

Findings / follow-ups:
- <concrete issue, coverage gap, or skipped operation>

Needs fixing:
- <issue and proposed fix, if any>
```

Use `PARTIAL` when the tested scope passed but requested coverage was unavailable.
Use `BLOCKED` when safe or authorized validation could not proceed. Do not make
code fixes during this workflow; report findings and ask separately before
editing source.
