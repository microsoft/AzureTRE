"""Verify that a branch caller holds the deployment lock before Azure work starts."""

import os
import re
import sys

from ci_environment_id import validate_ref
from recover_bootstrap_lease import RecoveryError, github, require, verify_concurrency

ACTIVE_RUN_STATUSES = frozenset(("in_progress", "queued", "pending", "waiting", "requested"))


def context():
    require(os.environ.get("GITHUB_ACTIONS") == "true", "Delegated deployment requires GitHub Actions.")
    ref = os.environ.get("CI_GIT_REF", "")
    validate_ref(ref)
    require(
        ref.startswith("refs/heads/") and ref == os.environ.get("GITHUB_REF"),
        "The delegated deployment reference differs from the branch caller.",
    )
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    require(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repository)
        and repository.split("/")[-1] not in (".", ".."),
        "Invalid deployment repository.",
    )
    values = [os.environ.get(key, "") for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")]
    require(
        all(value.isdecimal() and int(value) > 0 for value in values), "The deployment run identity is unavailable."
    )
    sha = os.environ.get("GITHUB_SHA", "")
    require(re.fullmatch(r"[0-9a-f]{40}", sha), "The deployment workflow commit is unavailable.")
    return {"ref": ref, "repository": repository, "run_id": int(values[0]), "attempt": int(values[1]), "sha": sha}


def verify_delegated_lock(ctx):
    run = github(ctx, f"/actions/runs/{ctx['run_id']}")
    require(
        isinstance(run, dict)
        and type(run.get("id")) is int
        and run["id"] == ctx["run_id"]
        and type(run.get("run_attempt")) is int
        and run["run_attempt"] == ctx["attempt"]
        and run.get("status") in ACTIVE_RUN_STATUSES
        and run.get("event") == "workflow_dispatch"
        and run.get("path") == ".github/workflows/deploy_tre_branch.yml"
        and run.get("head_branch") == ctx["ref"].removeprefix("refs/heads/")
        and run.get("head_sha") == ctx["sha"]
        and all(
            isinstance(run.get(key), dict) and run[key].get("full_name") == ctx["repository"]
            for key in ("repository", "head_repository")
        ),
        "The delegated deployment is not the current branch workflow run and attempt.",
    )
    # The parent run can be queued while a job executes. The canonical group's
    # in-progress owner, checked below, proves that this run holds the lock.
    members = verify_concurrency(ctx)
    # A reusable or job-level lease does not protect caller preparation.
    require(
        all("job_id" not in member for member in members if member["status"] == "in_progress"),
        "The branch caller does not hold a workflow-level deployment lock.",
    )


def main():
    try:
        delegated = os.environ.get("CI_DEPLOYMENT_LOCK_DELEGATED", "")
        require(delegated in ("true", "false"), "The deployment lock delegation flag is invalid.")
        if delegated == "false":
            print("The reusable workflow holds the deployment reference lock.")
            return 0
        verify_delegated_lock(context())
        print("The branch workflow owns the deployment reference lock for this run and attempt.")
    except (RecoveryError, ValueError, OSError) as error:
        print(f"ERROR: Deployment lock verification failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
