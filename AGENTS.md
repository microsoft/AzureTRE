# AzureTRE agent instructions

## Scope and repository map

These instructions apply to the repository. A nearer `AGENTS.md` or `CLAUDE.md` may add subsystem-specific rules; read it before editing that subtree.

AzureTRE is a Trusted Research Environment for secure research workspaces on Azure. The main areas are:

- `api_app/` — FastAPI API, persistence, services, and API tests
- `resource_processor/` — VMSS Porter/resource processing
- `airlock_processor/` — Airlock event processors
- `ui/` — frontend application
- `core/terraform/` — core Azure TRE infrastructure
- `devops/terraform/` — management/bootstrap infrastructure
- `templates/` — workspace and service bundles
- `e2e_tests/` — environment-dependent pytest tests
- `docs/` — MkDocs documentation
- `.github/workflows/` — CI/CD definitions

Prefer the nearest relevant code and tests over broad repository exploration. For uncommon workflows, read the linked procedure only when the task requires it.

## Working rules

- Inspect the existing implementation, tests, and relevant CI workflow before editing.
- Keep changes narrowly scoped; do not perform unrelated cleanup.
- Preserve existing user changes. Never discard a dirty working tree with `reset --hard`, `checkout -f`, `clean`, or an equivalent command.
- Do not commit, push, merge, publish, deploy, or destroy resources unless explicitly requested.
- Never place credentials, tokens, private environment files, or generated secrets in the repository or logs.
- Do not edit generated artifacts directly. Find the generator and update its source instead.
- Keep API contracts, schemas, migrations, bundle parameters, and their tests synchronized.

## Safety boundaries

Treat these as externally visible or state-changing operations and obtain explicit authorization immediately before running them unless the request clearly authorizes the specific operation and environment:

- `terraform apply`, `terraform destroy`, `make *deploy`, `make *destroy`, and Azure resource changes
- pushing images, publishing or registering bundles, and changing shared environments
- creating, deleting, or modifying workspaces and test data
- end-to-end tests against shared or production-like environments
- security, egress, or isolation probes

Prefer read-only inspection, formatting, focused tests, `terraform validate`, and `terraform plan` first. A plan is not approval to apply it. Use synthetic data and bounded test identities for authorized security or isolation checks.

## Validation

Run the narrowest relevant checks first, then expand as needed:

| Area | Focused validation | Broader validation |
|---|---|---|
| API | `cd api_app && python -m pytest <relevant-test> -q` | `cd api_app && python -m pytest tests_ma/test_api -q` |
| Resource processor | `cd resource_processor && python -m pytest <relevant-test> -q` | `cd resource_processor && python -m pytest tests_rp -q` |
| Airlock processor | `cd airlock_processor && python -m pytest <relevant-test> -q` | `cd airlock_processor && python -m pytest tests -q` |
| UI | Read `ui/` package scripts and run the relevant lint/typecheck/test command | UI build and applicable tests |
| Terraform | `terraform fmt -check -recursive` and `terraform validate` in the changed module | `terraform plan` in the approved environment |
| Documentation | `make lint-docs` | Documentation build |
| Repository | — | `make lint` (Docker-based, validates all files) |

E2E tests require environment configuration and may create cloud resources. Use the selectors and authorization procedure in `.claude/skills/pr-tester/SKILL.md` when validating a PR against Azure.

The top-level Makefile contains both safe validation and state-changing operations. Do not use `make all`, deployment, publishing, registration, or destruction targets as routine checks.

## Pull request validation

For PR validation, use `.claude/skills/pr-tester/SKILL.md` rather than inventing a deployment sequence. Resolve and record the exact PR head SHA, prefer an isolated worktree, do not implicitly merge or rebase onto `main`, scope builds and deployments to affected components, and verify deployed versions or digests match the PR before functional testing.

Never report a PR as passing without concrete evidence. If only local, unit, or partial functional checks ran, report the coverage boundary and use `PARTIAL` or `BLOCKED` where appropriate.

## Deeper procedures

Add or consult focused procedures under `docs/development/` when a workflow is substantial or uncommon, such as dependency upgrades, API-version changes, Terraform changes, releases, and E2E execution. Keep this file as an operating manual, not an architecture encyclopedia.

## Definition of done

- The requested behavior is implemented without placeholders.
- Focused tests and applicable lint, type, or validation checks were run.
- Generated outputs were refreshed where required.
- Relevant documentation was updated.
- No unrelated files were changed.
- Failures and skipped checks are reported with their exact reason.
- The final response identifies changed files and validation performed.
