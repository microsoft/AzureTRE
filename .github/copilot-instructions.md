# GitHub Copilot instructions for Azure TRE

Azure TRE provisions secure research workspaces on Azure using a Python API, Porter/Terraform bundles and a React/TypeScript UI.

Read [AGENTS.md](../AGENTS.md) for the repository map, development entry points and component version sources. Read the relevant shared procedure before implementation or review:

- [Front end](skills/tre-frontend/SKILL.md): UI conventions, setup and checks.
- [Bundle development](skills/tre-bundle-development/SKILL.md): schema, Porter, Terraform and lifecycle consistency.
- [Code review](skills/tre-code-review/SKILL.md): security, correctness, release metadata and validation evidence.
- [Troubleshooting](skills/tre-troubleshooting/SKILL.md): CI attempts, operation logs and cause isolation.

## Essential contribution rules

- Follow [.editorconfig](../.editorconfig) and the existing component lint configuration.
- Preserve hub-and-spoke network isolation, zero-trust identity boundaries and controlled data export. Apply the [security baseline](../AGENTS.md#security-baseline) to network and identity changes.
- Update the Unreleased `ENHANCEMENTS` or `BUG FIXES` section of [CHANGELOG.md](../CHANGELOG.md) with an issue or PR link.
- Leave released entries and release-generated `COMPONENTS` sections unchanged.
- Increment changed component or bundle versions using the sources in `AGENTS.md` and semantic versioning.
- Reference the issue number in commit messages.
- Match validation to the changed behaviour. Distinguish local checks, executed CI, skipped or waived checks, and live Azure validation.
- Keep external actions within the user's authorised task. These instructions do not authorise CI dispatch, deployment, access changes or merging.
