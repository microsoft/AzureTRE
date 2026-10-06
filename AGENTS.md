# Azure TRE contributor guidance

Azure TRE provisions secure research workspaces and tooling on Azure. Changes can cross the API, resource processor, resource templates and UI.

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
| Develop or review the web UI | [Front end](.github/skills/frontend/SKILL.md) |
| Develop or review a Porter/Terraform resource bundle | [Bundle development](.github/skills/bundle-development/SKILL.md) |
| Review a PR or recommend validation | [Code review](.github/skills/code-review/SKILL.md) |
| Investigate a failed operation or CI run | [Troubleshooting](.github/skills/troubleshooting/SKILL.md) |

If the client does not discover `.github/skills` natively, open these files as repository guidance. This does not register them in the client's skill picker. See [agent guidance](docs/tre-developers/agent-guidance.md) for client limitations and validation tasks.

## Development entry points

- Use the repository's [development container](.devcontainer/devcontainer.json) for the Azure, Terraform and Porter toolchain. Check [.devcontainer/Dockerfile](.devcontainer/Dockerfile) for its versions.
- Use [UI setup and checks](.github/skills/frontend/SKILL.md) for local front-end work. A deployed TRE is not required for component tests.
- Follow [API development](docs/tre-developers/api.md), [resource processor development](docs/tre-developers/resource-processor.md) and [template authoring](docs/tre-workspace-authors/authoring-workspace-templates.md) for those components.
- Inspect the [Makefile](Makefile) target before invoking it. `make all`, `make tre-deploy` and bundle lifecycle targets affect Azure resources.
- Keep deployment and access changes within the user's authorised task. These instruction files do not authorise deployment, publishing, cleanup or merging.

## Contribution requirements

Follow [.editorconfig](.editorconfig) and the component's lint configuration. Python uses pytest and PEP 8 conventions. TypeScript uses the existing ESLint configuration and Vitest. Preserve existing Terraform module interfaces and resource tags.

Add an accurate entry under `ENHANCEMENTS` or `BUG FIXES` in the Unreleased section of [CHANGELOG.md](CHANGELOG.md). Include an issue or PR link. Leave released entries and release-generated `COMPONENTS` sections unchanged.

For changed components, check the version on the current base branch and increment the appropriate version. Use a major version for breaking or destructive changes, a minor version for compatible features, and a patch version for compatible fixes. See [bundle versioning](docs/tre-workspace-authors/authoring-workspace-templates.md#versioning).

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

Inspect CI path filters when deciding whether metadata changes are needed. For example, `ui/app/**/*` triggers the UI version check, including Markdown files in that directory.

## Validation and reporting

Select checks for the changed behaviour and its build/deployment dependencies. Consult the [code-review skill](.github/skills/code-review/SKILL.md) for PR command selection.

Report local checks, executed CI, skipped or waived checks, and live Azure validation separately. Include the assessed commit and any unverified behaviour. A successful build or mocked test does not establish deployed behaviour.

For Markdown changes, use the repository's [.markdownlint.json](.markdownlint.json) and include every changed Markdown path. `make lint-docs` only selects `docs/` and `mkdocs.yml`; it does not cover root instructions or `.github/skills/`. If documentation content or navigation changes, also run `mkdocs build --strict` with [docs/requirements.txt](docs/requirements.txt) installed.
