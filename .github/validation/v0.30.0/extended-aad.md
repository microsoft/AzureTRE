# v0.30.0 AAD-command validation

Tracking issue: [#5134](https://github.com/microsoft/AzureTRE/issues/5134).
Release: [#5119](https://github.com/microsoft/AzureTRE/issues/5119).

This draft validation PR provides an isolated command and investigation thread.
Close it after recording the results. It is not intended for merge.

## Candidate and scope

- Application and workflow baseline: `1071bf21749504be57550a9742fc87c521059ca2`.
- The only change from that baseline is this validation record.
- Run `/test-extended-aad` with full deployment, smoke tests and the `extended_aad` selector.
- Use this PR's distinct environment alongside the extended-command environment on #5164.
- Keep the release campaign at two active environments and repeated runs on each PR sequential.

The selected case creates a workspace with an automatically provisioned identity,
deploys Guacamole and checks its authentication redirect.
It does not create a Windows VM or prove every Entra role and tenant-isolation boundary.
This command does not support `skip_deployment`.

## Evidence

Record results in #5134 and the PR thread so evidence updates do not move the tested head.

- Record the PR head, actual checked-out merge SHA and workflow revision.
- Record the PR ref, derived TRE ID, cloud, region, run URL and attempt.
- Record capacity checks, remaining uncertainties and the companion extended run.
- Confirm that the bot selects `extended_aad` and that deployment and tests execute.
- Record passed, failed and skipped tests separately, with reasons.
- Link failures to focused defect issues and any subsequent fix/retest.
- Record cleanup or explicit retention ownership for the validation environment.

A documentation-only `/test` status can be a waiver. It is not evidence for this case.
Do not mark this validation complete until the observed results support it.
