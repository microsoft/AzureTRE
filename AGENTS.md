# Azure TRE contributor guidance

Azure TRE provisions secure research workspaces and tooling on Azure. Changes can cross the API, resource processor, resource templates and UI.

## Security baseline

Azure TRE uses hub-and-spoke networking, Microsoft Entra ID and a zero-trust model with strict workspace boundaries. Preserve the intended network isolation and controlled data import/export through Airlock.

For network or identity changes, assess outbound access, firewall FQDN rules, private endpoints, public network access and managed-identity/RBAC scope. Justify expanded access and check whether it creates a path around workspace isolation or Airlock. Apply the relevant component skill for detailed checks.

## Repository map

| Path | Responsibility |
| --- | --- |
| `api_app/` | FastAPI API, resource models and template validation |
| `resource_processor/` | Service Bus request handling and Porter bundle execution |
| `airlock_processor/` | Airlock event processing and data movement |
| `ui/app/` | React, TypeScript, Fluent UI and MSAL web application |
| `core/terraform/` | Core Azure infrastructure |
| `templates/` | Workspace, workspace-service, shared-service and nested user-resource bundles |
| `cli/` | TRE command-line client |
| `devops/` | Deployment, configuration and CI environment scripts |
| `e2e_tests/` | Tests against a deployed TRE |
| `.github/workflows/` and `.github/scripts/` | CI definitions and PR comment bot |
| `docs/` and `mkdocs.yml` | Documentation and site navigation |

## Start with the relevant skill

Shared procedures live in `.github/skills/`. Read the relevant `SKILL.md` before changing or reviewing that component. Load only the skills needed for the task.

| Task | Skill |
| --- | --- |
| Develop or review the web UI | [Front end](.github/skills/tre-frontend/SKILL.md) |
| Develop or review a Porter/Terraform resource bundle | [Bundle development](.github/skills/tre-bundle-development/SKILL.md) |
| Review a PR or recommend validation | [Code review](.github/skills/tre-code-review/SKILL.md) |
| Investigate a failed operation or CI run | [Troubleshooting](.github/skills/tre-troubleshooting/SKILL.md) |

If the client does not discover `.github/skills` natively, open these files as repository guidance. This does not register them in the client's skill picker. See [agent guidance](docs/tre-developers/agent-guidance.md) for client limitations and validation tasks.

## Development entry points

- Use the repository's [development container](.devcontainer/devcontainer.json) for the Azure, Terraform and Porter toolchain. Check [.devcontainer/Dockerfile](.devcontainer/Dockerfile) for its versions.
- Use [UI setup and checks](.github/skills/tre-frontend/SKILL.md) for local front-end work. A deployed TRE is not required for component tests.
- Follow [API development](docs/tre-developers/api.md), [resource processor development](docs/tre-developers/resource-processor.md) and [template authoring](docs/tre-workspace-authors/authoring-workspace-templates.md) for those components.
- Inspect the [Makefile](Makefile) target before invoking it. `make all`, `make tre-deploy` and bundle lifecycle targets affect Azure resources.
- Keep deployment and access changes within the user's authorised task. These instruction files do not authorise deployment, publishing, cleanup or merging.

## Contribution requirements

Follow [.editorconfig](.editorconfig) and the component's configured test runner, linter and formatter. Preserve existing Terraform module interfaces and resource tags.

Read [.pre-commit-config.yaml](.pre-commit-config.yaml), the [Makefile](Makefile) and affected CI jobs for the tools selected by the checked-out revision. Run applicable hooks with `pre-commit run --files <changed-files>` and inspect automatic fixes before staging. Keep formatting within the PR's scope.

Add an accurate entry under `ENHANCEMENTS` or `BUG FIXES` in the Unreleased section of [CHANGELOG.md](CHANGELOG.md). Include an issue or PR link. Leave released entries and release-generated `COMPONENTS` sections unchanged. Reference the issue number in commit messages.

For changed components, check the version on the current base branch and increment the appropriate version. Use a major version for breaking or destructive changes, a minor version for compatible features, and a patch version for compatible fixes. See [bundle versioning](docs/tre-workspace-authors/authoring-workspace-templates.md#versioning).

Refresh the target repository's base ref, such as `upstream/main` for a fork. After each merge or rebase, recheck component versions and Unreleased changelog entries against that ref. Inspect the PR diff for unrelated files or formatting introduced during conflict resolution.

| Component | Version source |
| --- | --- |
| API | `api_app/_version.py` |
| Resource processor | `resource_processor/_version.py` |
| Airlock processor | `airlock_processor/_version.py` |
| UI | `ui/app/package.json` and corresponding lockfile metadata |
| Core | `core/version.txt` |
| DevOps | `devops/version.txt` |
| CLI | `cli/setup.py` |
| Porter bundle | The changed bundle's `porter.yaml` |
| Guacamole server image | `templates/workspace_services/guacamole/guacamole-server/docker/version.txt` |
| Gitea image | `templates/shared_services/gitea/docker/version.txt` |
| GitHub scripts | `.github/scripts/package.json` and corresponding lockfile metadata |

Formatting-only changes can still require component version bumps. Inspect CI path filters when deciding whether metadata changes are needed. For example, `ui/app/**/*` triggers the UI version check, including Markdown files in that directory.

## Validation and reporting

Select checks for the changed behaviour and its build/deployment dependencies. Consult the [code-review skill](.github/skills/tre-code-review/SKILL.md) for PR command selection.

Match CI's working directory, runtime, dependencies and environment, including `PYTHONPATH` where configured. See the [E2E helper workflow](.github/workflows/e2e_helper_tests.yml) for an example. Use finite timeouts suited to the selected checks. If a check times out, inspect its process and logs before retrying and report it as incomplete.

If repeated reviews expose failures in the same design, reassess its coordination and recovery before adding more patches. Mocked unit tests alone do not establish distributed concurrency or message-redelivery behaviour.

Report local checks, executed CI, skipped or waived checks, and live Azure validation separately. Include the assessed commit and any unverified behaviour. A successful build does not establish deployed behaviour.

When publishing is part of the authorised task, verify that the remote PR branch contains the reported commit before reporting completion. Provide its SHA and distinguish the tested commit from a later PR head. For local-only work, report that the commit remains unpublished.

For Markdown changes, use the repository's [.markdownlint.json](.markdownlint.json) and include every changed Markdown path. `make lint-docs` only selects `docs/` and `mkdocs.yml`; it does not cover root instructions or `.github/skills/`. If documentation content or navigation changes, also run `mkdocs build --strict` with [docs/requirements.txt](docs/requirements.txt) installed.
