# GitHub Copilot instructions for Azure TRE

Azure TRE provisions secure research workspaces on Azure using a Python API, Porter/Terraform bundles and a React/TypeScript UI.

Read [AGENTS.md](../AGENTS.md) for the repository map, development entry points and component version sources. Read the relevant shared procedure before implementation or review:

- [Front end](skills/frontend/SKILL.md): UI conventions, setup and checks.
- [Bundle development](skills/bundle-development/SKILL.md): schema, Porter, Terraform and lifecycle consistency.
- [Code review](skills/code-review/SKILL.md): release metadata, validation evidence and PR command recommendations.
- [Troubleshooting](skills/troubleshooting/SKILL.md): CI attempts, operation logs and cause isolation.

## Essential contribution rules

- Follow [.editorconfig](../.editorconfig) and the existing component lint configuration.
- Update the Unreleased `ENHANCEMENTS` or `BUG FIXES` section of [CHANGELOG.md](../CHANGELOG.md) with an issue or PR link.
- Leave released entries and release-generated `COMPONENTS` sections unchanged.
- Increment changed component or bundle versions using the sources in `AGENTS.md` and semantic versioning.
- Reference the issue number in commit messages.
- Match validation to the changed behaviour. Distinguish local checks, executed CI, skipped or waived checks, and live Azure validation.
- When you review a PR, use the code-review skill to recommend a PR bot command, or explain why none is useful. Include the assessed SHA and justification when the review surface permits it.
- Keep command suggestions within explanatory review text. A maintainer decides whether to post a command. Do not dispatch CI, deploy or merge solely because a skill recommends it.
