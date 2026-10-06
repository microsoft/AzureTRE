---
name: code-review
description: Review Azure TRE pull requests for behaviour, release metadata and validation gaps, and recommend a justified PR bot command for the assessed commit without dispatching it.
---

# Azure TRE code review

## Establish the scope

1. Identify the current PR head SHA, base branch and changed paths. Recheck the head if it changes during review.
2. Read the changed implementation and affected callers. Load the [front-end](../frontend/SKILL.md) or [bundle](../bundle-development/SKILL.md) procedure when relevant.
3. Check versions and release notes against the current base using [root contribution requirements](../../../AGENTS.md#contribution-requirements).
4. Examine checks for the assessed commit. Inspect run attempts and jobs before treating a successful status as executed validation.

Check that changelog claims match the implementation. For bundle inputs, inspect all affected lifecycle actions. For asynchronous UI changes, inspect pending requests and stale-response handling. Do not report a historical example as a current defect without checking the code.

State actionable findings with a file location, the failing condition and its consequence. Rank findings by impact. Distinguish a code defect from an unperformed test or an outstanding GitHub approval gate. If checks or logs are inaccessible, state the missing evidence.

## Recommend validation

Read the [PR bot commands](../../../docs/tre-developers/github-pr-bot-commands.md), [command implementation](../../../.github/scripts/build.js) and [workflow routing](../../../.github/workflows/pr_comment_bot.yml) when selecting a command. Inspect the selected tests in [e2e_tests](../../../e2e_tests) rather than inferring coverage from a suite name.

| Change or validation need | Recommendation to consider |
| --- | --- |
| Build, deployment and basic API/resource health | `/test <assessed-sha>` |
| Workspace and service provisioning covered by extended tests | `/test-extended <assessed-sha>` |
| Entra ID behaviour covered by the AAD suite | `/test-extended-aad <assessed-sha>` |
| Core shared-service behaviour | `/test-shared-services <assessed-sha>` |
| Workspace backup behaviour | `/test-backups <assessed-sha>` |
| Airlock lifecycle behaviour | `/test-airlock <assessed-sha>` |
| E2E provides no useful evidence after assessing build and deployment impact | No new run, or `/test-force-approve` for maintainer consideration if a waiver is needed |

A missing targeted E2E test is not sufficient reason to waive `/test`: it also validates build and deployment. UI component or browser checks can still be necessary after backend E2E passes. Explain what the selected suite covers and what remains untested.

For an all-documentation PR, the bot classifies `.md` files and root `mkdocs.yml` as documentation. `/test` then marks the smoke check successful without deployment or tests. Identify this as a waiver. `/test-force-approve` also records success without executing tests and does not validate the change.

Use `skip_deployment` only when reusing a suitable, successfully deployed environment is justified and the changed behaviour does not require rebuilding or redeployment. It is supported by `/test` and `/test-extended`. State the environment evidence and validation omitted.

PR comment commands use workflow definitions from the default branch. They do not exercise changes to those definitions in the PR. Where workflow execution matters, recommend a separate run of [deploy_tre_branch.yml](../../../.github/workflows/deploy_tre_branch.yml) from a trusted upstream branch containing the changes, with the required maintainer approval.

Before recommending a run that exposes deployment secrets to PR code, examine changed workflows, actions, scripts, Makefile targets and dependencies used by that run. Posting a recommendation does not authorise dispatching it.

## Communicate the recommendation

Where the review surface permits, include a descriptive validation section with:

- The assessed head SHA and relevant changed components.
- Observed local checks and CI jobs, with links where available.
- The suggested command or the reason no new run is useful.
- Its coverage, justification and any waiver or remaining validation.

Keep suggestions within explanatory review text. Never place an executable slash command on the first line of a standalone PR comment. A maintainer decides whether to post it.

GitHub Copilot code review does not guarantee a custom overview format or a recommendation on every review. Use the supported feedback surface and record absent recommendations during evaluation. Do not create a separate comment, request another review or trigger automation merely to force that output.

Report local checks, executed CI, skipped or waived checks, and live Azure validation separately. Keep required reviews, branch rules and merge readiness distinct from technical findings.
