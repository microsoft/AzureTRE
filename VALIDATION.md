# Post-merge command validation

This temporary draft validates the merged PR-comment routes for shared services and Airlock.
The executable code matches main at `0c5027e990d6832e21bafc1dc004594e9e945d1d`.

Run shared-service validation with explicit Nexus consent, then Airlock validation on the same PR.
Record the checked-out revision, selected cases, skips and cleanup results in the PR description.

This draft is not intended for merge. Close it after validation.
Cleanup coordination and branch inactivity checks remain separate in issue #5231.

Related work: [#5119](https://github.com/microsoft/AzureTRE/issues/5119).
