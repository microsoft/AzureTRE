# Agent guidance for contributors

Azure TRE shares repository context through root `AGENTS.md` and reusable procedures through `.github/skills`. GitHub Copilot is the primary target. Other agents can read the same files as repository guidance.

## File layout

| File | Purpose |
| --- | --- |
| `AGENTS.md` | Repository map, contribution requirements and links to the relevant skills |
| `.github/copilot-instructions.md` | Essential Copilot rules and links to the shared guidance |
| `.github/skills/frontend/SKILL.md` | UI setup, conventions and validation |
| `.github/skills/bundle-development/SKILL.md` | Bundle contracts and lifecycle checks |
| `.github/skills/code-review/SKILL.md` | Review procedure and PR command recommendations |
| `.github/skills/troubleshooting/SKILL.md` | Failure evidence and cause isolation |

Start with the [root instructions](https://github.com/microsoft/AzureTRE/blob/main/AGENTS.md). Keep each detailed procedure in its skill. The short Copilot file retains essential rules for surfaces that do not automatically load `AGENTS.md`. Scoped instruction files and additional discovery adapters can be added when a demonstrated need justifies them.

These files guide existing sessions. They do not create scheduled automation, change review settings, post PR bot commands or grant permission to deploy or merge.

## Client compatibility

The following expectations are based on product documentation checked on 6 October 2026. They describe documented support, not completed client acceptance tests.

| Client or surface | Expected behaviour and limitation |
| --- | --- |
| Copilot cloud agent, including issue-assignee sessions | Supports root `AGENTS.md` and repository skills. Verify both discovery and application in a fresh task. |
| Copilot code review on GitHub | Supports root `AGENTS.md` and skills in `.github/skills`. The review skill uses the review-focused name `code-review`. Instructions and skills are read from the PR head branch. |
| Copilot CLI | Supports root `AGENTS.md` and `.github/skills`. Use `/skills list` and `/skills info <name>` to inspect discovery. Reload skills or start a fresh session after changes. |
| Copilot agent sessions in VS Code | Supports root `AGENTS.md` and `.github/skills`. Record the selected agent harness and instruction settings. The Local agent can disable `AGENTS.md` through `chat.useAgentsMdFile`. |
| Copilot code review in VS Code | The support matrix lists `.github/copilot-instructions.md`. Do not infer support for every instruction type from the agent-session behaviour. |
| GitHub Copilot app | Repository and CLI skills are documented as available. Confirm root instruction loading and skill use in the installed app. |
| Codex | Reads root `AGENTS.md`. Its documented native repository skill location is `.agents/skills`. Follow the root links to read these skills as guidance; this does not promise native skill-picker registration. |

Sources: [GitHub instruction support](https://docs.github.com/en/copilot/reference/custom-instructions-support), [Copilot skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills), [GitHub code review](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/copilot-code-review).

Additional sources: [Copilot CLI skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills), [VS Code instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions), [Copilot app customisation](https://docs.github.com/en/copilot/how-tos/github-copilot-app/customize-github-copilot-app).

Codex sources: [repository instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [skill discovery](https://learn.chatgpt.com/docs/build-skills).

GitHub documents custom review-overview formatting as [unsupported](https://docs.github.com/en/copilot/tutorials/customize-code-review#unsupported-instruction-types). The review skill requests a justified test recommendation where the surface permits it. Record whether a recommendation appears; do not claim that the files guarantee one on every review.

## Validate changes to the guidance

### Static checks

1. Check each skill's YAML frontmatter for a unique `name` matching its directory and a concise `description`.
2. Resolve local links and check the referenced paths and commands against the current repository.
3. Lint every changed Markdown file using `.markdownlint.json`.
4. If documentation content or navigation changes, install `docs/requirements.txt` and run `mkdocs build --strict`.
5. Run `git diff --check`.

With `markdownlint-cli` installed, this command checks the shared guidance from the repository root:

```bash
markdownlint --config .markdownlint.json AGENTS.md .github/copilot-instructions.md '.github/skills/*/SKILL.md' docs/tre-developers/agent-guidance.md
```

Include other changed Markdown files in the invocation. `make lint-docs` excludes root instructions and `.github/skills`, so it is not sufficient for this change.

For an all-documentation PR, `/test` produces a smoke-check waiver under the current [PR bot implementation](https://github.com/microsoft/AzureTRE/blob/main/.github/scripts/build.js). It does not test skill discovery. Select any PR command using the [code-review procedure](https://github.com/microsoft/AzureTRE/blob/main/.github/skills/code-review/SKILL.md) and [PR bot documentation](github-pr-bot-commands.md).

### Client and behaviour checks

1. Start a fresh session against the branch containing the guidance.
2. Record the client version, agent harness, relevant settings and repository SHA.
3. Check discovery using the client's skill list, references or session logs where available.
4. Give the agent a representative task without pasting repository guidance or the expected finding.
5. Check the produced work and tool activity against the expected behaviour below.
6. Record discovery, invocation and behaviour separately as passed, failed or not tested.

Use a disposable branch or a supplied diff for regression examples. Do not reintroduce historical defects into the product PR. Keep review posting, CI dispatch and Azure changes within the authorised evaluation scope.

| Scenario | Expected behaviour |
| --- | --- |
| UI filter or workspace changes during a pending request | Reads the UI procedure, considers follow-up requests and stale responses, and chooses relevant component checks. |
| A new Terraform input is supplied only during install | Checks upgrade and uninstall and identifies any missing input or suitable default. |
| API behaviour changes without a new API version | Checks the current base version and identifies the release metadata gap. |
| A release note claims a field that the UI does not render | Compares the implementation and tests with the note and identifies the mismatch. |
| CI deployment fails before E2E starts | Identifies the run attempt, checked-out commit and first relevant failure. Reports the tests as unexecuted. |
| Documentation-only PR review | Justifies the checks needed and identifies any successful smoke status created by a waiver. |

Historical examples: [bundle uninstall input](https://github.com/microsoft/AzureTRE/pull/5100#discussion_r4104200195), [API version](https://github.com/microsoft/AzureTRE/pull/5100#discussion_r4186456098), [UI refresh race](https://github.com/microsoft/AzureTRE/pull/5105#discussion_r4173077326), [release-note accuracy](https://github.com/microsoft/AzureTRE/pull/5105#discussion_r4173077339).

For GitHub review, record the PR head, review URL and any skill attribution or session-log evidence. Evaluate the test recommendation's SHA, coverage, observed checks and justification. Record missing or misplaced recommendations as a limitation. A skill appearing in a list establishes discovery only; it does not prove that the agent used it correctly.

Keep dated validation results in the PR or linked issue, including untested clients and missing evidence. Recheck relevant clients after changing discovery paths or skill descriptions.
