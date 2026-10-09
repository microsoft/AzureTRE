# v0.30.0 extended-command validation

Tracking issue: [#5133](https://github.com/microsoft/AzureTRE/issues/5133).
Release: [#5119](https://github.com/microsoft/AzureTRE/issues/5119).

This draft validation PR provides an isolated command and investigation thread.
Close it after recording the results. It is not intended for merge.

## Candidate and scope

- Application and workflow baseline: `1071bf21749504be57550a9742fc87c521059ca2`.
- The only change from that baseline is this validation record.
- First run: `/test-extended` with full deployment, smoke tests and the `extended` selector.
- Follow-up after a successful full run: the same command with `skip_deployment` against the matching environment.
- Start one environment and keep both runs sequential on this PR.

The existing extended cases create unrestricted and Airlock import-review workspaces,
and provision Guacamole and a Windows VM in a base workspace.
They do not select the separate `workspace_services`, `linux_vm`, `extended_aad`,
`shared_services`, `backups` or `airlock` suites.

## Evidence

Record results in #5133 and the PR thread so evidence updates do not move the tested head.

- Record the PR head, actual checked-out merge SHA and workflow revision.
- Record the PR ref, derived TRE ID, cloud, region, run URL and attempt.
- Confirm that the bot selects `extended` and that deployment and tests execute.
- Record passed, failed and skipped tests separately, with reasons.
- Link failures to focused defect issues and any subsequent fix/retest.
- Record cleanup or explicit retention ownership for the validation environment.

A documentation-only `/test` status can be a waiver. It is not evidence for this case.
Do not mark this validation complete until the observed results support it.
