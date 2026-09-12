# AVD v1 Validation

Validation covers the local AVD v1 review fixes, before pushing them for review.
Standard management was tested, not automated Session Host Configuration.
Normal AVD current version remains 0.6.2.

## Passed

- Nine schema/catalogue/workflow/bootstrap regression tests.
- Ten registration initialization retry tests.
- Terraform validation: core, base, parent and child.
- Porter lint and parent/child image builds; bootstrap SHA-256 verification.
- Published both v1 bundles to the development ACR as non-current templates.
- Published a validation-only parent alias with the same bundle digest.
- Published parent image initializes and validates successfully.
- Live prerequisites: 25H2 images available, AVD DNS links completed,
  resource processor has workspace Storage Blob Data Contributor.

## Live Tests

Workspace: `22909d7c-32cb-424d-a6d9-cfaf60849a4e`.
Test-only template: `tre-service-avd-v1-validation` version `1.0.0`.

- Pooled service: `bfe8e4d7-54d5-4bac-aec7-cfc591ee2e22`.
  Install operation: `e9ee0d15-0d5e-401d-a749-649b6a01d225`.
  One D4s_v6 host, 25H2 multi-session, client-to-session clipboard.
- Personal service: `34d499ec-75d8-4f88-8ab0-6a59fa2788f3`.
  Install operation: `904a88f5-bcca-490e-81f8-22746f3ef957`.
  Clipboard disabled; parent deployed successfully.
- Personal child: `2d2622c5-2df5-4400-b853-b794c469390a`.
  Install operation: `ed14977d-de2d-4088-8af6-613468df72d4`.
  25H2 Enterprise, 2 CPU / 8 GB, assigned to the existing user identity.

Pooled first install reached VM creation but failed in CustomScriptExtension:
`The command line is too long.` The local pooled bootstrap now uses the same
UTF-8 wrapper as the personal host instead of UTF-16 EncodedCommand. Validation
and a new command-length regression test pass (5,544 characters with a
2,048-character token, below the 8,191-character limit). Corrected image built
and published; the final live retry succeeded.

The pooled VM confirms `win11-25h2-avd` version `26200.9445.260908`,
`Premium_LRS`, `Windows_Client`, encryption at host, Trusted Launch,
Secure Boot and vTPM.

Pooled retry `22807626-5994-42d3-8534-28ea77792646` used the corrected image
but found the failed extension from the first attempt outside Terraform state.
That failed test extension was deleted, leaving the VM and policy in place.
Retry operation: `44d10238-3fff-4171-ab45-0021e244e3de`.

Both personal child and pooled retry completed successfully. Both hosts became
`Available` in AVD. The personal host was assigned to the requested existing user.
Guest checks confirmed running RDAgentBootLoader and successful Entra join.
Pooled clipboard policy: SCClipLevel=0, CSClipLevel=4 (client-to-session only).
Personal clipboard policy: SCClipLevel=0, CSClipLevel=0 (disabled).
Both guests booted after their recorded policy application boot timestamp.

## Scaling Blocker

PATCH of `pooled_session_host_count` from 1 to 2 returned HTTP 400:
`Unevaluated properties are not allowed ('pooled_session_host_count' was unexpected)`.
The shared API `ResourceRepository.validate_patch` validates only the partial
patch, so the conditional schema cannot see the existing `host_pool_type`.
The schema's updateable flag is necessary but insufficient. No scale-out or
scale-in occurred. A shared API fix needs separate scope and regression tests.
The relevant PR review thread has been updated with this live finding.

## Cleanup

- Personal child deletion: `c2b3d979-e5a4-4338-88b5-97e10cad9bcc` (confirmed:
  TRE child list empty and VM `avd9a4e88f3390a` absent).
- Pooled service deletion: `f455e8bd-9d29-4ca3-9ecb-91bf386bcfe1` (confirmed:
  TRE service absent and no matching Azure resources for test suffix `2e22`).
- Personal parent disable: `a318501b-94b1-4ac1-bf18-ca925c3fb5a7` (updated).
- Personal parent deletion: `4ba498d0-bcc9-42f4-8a09-0a0819d68e52` (confirmed:
  TRE service absent).
- Final checks: no validation-template services remain in TRE and no matching
  Azure resources remain in the workspace resource group for test suffixes
  `2e22`, `88f3` or `390a`.
- Shared AVD private DNS zone and both VNet links remain in `Succeeded` state;
  the resource processor retains workspace Storage Blob Data Contributor.
- Validation template registrations and development ACR artifacts are retained.

## Unverified

- Fresh core/base provisioning. Live workspace is already 2.11.0 and will not
  be downgraded to local base 2.9.0; DNS/RBAC prerequisites already exist.
- Cross-subscription deployment, optional SSO pre-consent, GitHub Actions run.
- Interactive Windows sign-in and actual client clipboard behavior.
- Scale-out and scale-in are blocked as described above.

Older failed cleanup operations are separate and untouched by this test.
All 15 PR review threads now have replies describing the local changes and
verification limits. Threads remain unresolved because code is not pushed.

Resource processor health check: running, root filesystem 50% used with 32 GB free.

## Security Follow-up

The failed operation's stored diagnostic message includes an authentication
client secret in Terraform command arguments. The value is intentionally not
copied here. Rotate the affected credential and address operation-log redaction;
neither credential rotation nor broad logging changes were performed in this test.