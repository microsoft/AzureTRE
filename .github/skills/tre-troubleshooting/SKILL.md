---
name: tre-troubleshooting
description: Uses the exact commit, run attempt and component logs to separate observed causes from hypotheses. Use when you investigate a failed Azure TRE deployment, bundle operation or GitHub Actions run.
---

# Azure TRE troubleshooting

## Identify the failing operation

Record the PR or branch, assessed head SHA, workflow run and attempt, failing job and step, and the relevant time window. For deployed failures, also identify the TRE, component or bundle version, resource ID and operation ID where available.

Distinguish the requested PR head from the commit actually checked out by the workflow. Inspect checkout steps, workflow inputs and logs; a run's headline SHA alone may not identify the deployed code.

For GitHub Actions, inspect a specific attempt with GitHub CLI when available:

```bash
gh run view <run-id> --repo microsoft/AzureTRE --attempt <attempt-number>
gh run view <run-id> --repo microsoft/AzureTRE --attempt <attempt-number> --log-failed
```

If the failed-job output is incomplete, inspect the relevant step and its preceding output in the full attempt logs. Do not combine failures from different attempts into one causal sequence.

## Select the evidence source

| Failure stage | Evidence to inspect |
| --- | --- |
| Dependency, lint or unit-test failure | Exact command, runtime version, lockfile, full error and component test results |
| Management or core deployment | Terraform diagnostics, backend state/lock messages, workflow inputs and relevant Azure operation results |
| Bundle action | TRE operation status, resource processor logs, Porter action and underlying Terraform or script error |
| API request | Response status, resource/operation correlation and API traces |
| Airlock processing | Request stage, event/function logs and relevant storage operations |
| UI failure | Browser request and console evidence, user roles, workspace identity and component state |

Use [Application Insights queries](../../../docs/troubleshooting-faq/app-insights-logs.md), [resource processor diagnostics](../../../docs/troubleshooting-faq/troubleshooting-rp.md), [API logs](../../../docs/troubleshooting-faq/api-logs-deployment-center.md) and [Airlock diagnostics](../../../docs/troubleshooting-faq/airlock-troubleshooting.md) as appropriate.

Keep tokens, credentials and sensitive research data out of shared logs and reports. Capture the relevant diagnostic excerpt and correlation identifiers instead of copying an unrestricted log archive.

## Isolate the cause

Find the earliest error that explains the failure. A later wrapper timeout or summary can hide the underlying Terraform, Azure or application error. Separate a failed deployment from tests that never ran, and separate cleanup failures from the original failure.

For each likely cause, state the supporting observation and the next check that would distinguish it from alternatives. Compare the tested commit, inputs and environment with a known working case where available. Treat quota, regional availability, permissions and retained Azure resources as hypotheses until verified.

Prefer read-only checks and a scoped local reproduction before changing infrastructure. Do not release a state lock, purge a resource, alter access or destroy an environment solely to clear an error. Those actions require an authorised recovery task and evidence identifying the affected environment and owner.

## Report and follow up

State what failed, the observed cause or leading hypothesis, missing evidence and the next diagnostic step. Include the run attempt and commit with supporting links.

When a repair is authorised, use the component's procedure and verify the repaired path. Report the results according to the [root reporting rules](../../../AGENTS.md#validation-and-reporting). Use the [code-review skill](../tre-code-review/SKILL.md) for any PR test recommendation. A queued run, skipped job or manually successful check is not an executed test.
