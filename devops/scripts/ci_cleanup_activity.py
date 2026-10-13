"""Defer scoped cleanup while matching validation is active or recently used a branch."""

from datetime import datetime, timezone
from urllib.parse import urlencode

from recover_bootstrap_lease import RecoveryError, github, require

ACTIVE_STATUSES = frozenset(("in_progress", "queued", "pending", "waiting", "requested"))
CLEANUP_WORKFLOW = ".github/workflows/clean_validation_envs.yml"
BRANCH_WORKFLOW = ".github/workflows/deploy_tre_branch.yml"


def pending_work(ctx, members):
    """Ignore only identified cleanup successors in the validated reference queue."""
    for member in members:
        if member["status"] == "in_progress":
            continue  # verify_concurrency already proved this is the current cleanup owner.
        run = github(ctx, f"/actions/runs/{member['run_id']}")
        require(
            isinstance(run, dict)
            and run.get("id") == member["run_id"]
            and isinstance(run.get("repository"), dict)
            and run["repository"].get("full_name") == ctx["repository"],
            "Cannot identify queued cleanup work.",
        )
        if run.get("path") != CLEANUP_WORKFLOW or run.get("event") not in ("schedule", "workflow_dispatch"):
            return True
        if "job_id" not in member:
            return True
        job = github(ctx, f"/actions/jobs/{member['job_id']}")
        if not (
            isinstance(job, dict)
            and job.get("id") == member["job_id"]
            and job.get("run_id") == member["run_id"]
            and type(run.get("run_attempt")) is int
            and run["run_attempt"] > 0
            and job.get("run_attempt") == run["run_attempt"]
            and job.get("name") == "Clean " + ctx["ref"]
            and job.get("status") in ACTIVE_STATUSES
        ):
            return True
    return False


def timestamp(value):
    require(isinstance(value, str), "Missing branch validation timestamp.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RecoveryError("Invalid branch validation timestamp.") from error
    require(result.tzinfo is not None, "Branch validation timestamp has no time zone.")
    return result.timestamp()


def branch_activity(ctx, commit_time, now=None):
    """Read all matching branch runs, including old runs with recent rerun activity."""
    require(
        ctx["ref"].startswith("refs/heads/") and type(commit_time) is int and commit_time > 0,
        "Invalid branch cleanup activity request.",
    )
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    branch = ctx["ref"].removeprefix("refs/heads/")
    latest = commit_time
    runs, total = {}, None
    for page in range(1, 12):
        query = urlencode({"branch": branch, "event": "workflow_dispatch", "per_page": 100, "page": page})
        data = github(ctx, "/actions/workflows/deploy_tre_branch.yml/runs?" + query)
        require(
            isinstance(data, dict)
            and type(data.get("total_count")) is int
            and 0 <= data["total_count"] <= 1000
            and isinstance(data.get("workflow_runs"), list),
            "Incomplete branch validation history.",
        )
        total = data["total_count"] if total is None else total
        require(total == data["total_count"], "Branch validation history changed during cleanup.")
        for run in data["workflow_runs"]:
            require(
                isinstance(run, dict)
                and type(run.get("id")) is int
                and run["id"] > 0
                and run["id"] not in runs
                and run.get("path") == BRANCH_WORKFLOW
                and run.get("event") == "workflow_dispatch"
                and run.get("head_branch") == branch
                and all(
                    isinstance(run.get(key), dict) and run[key].get("full_name") == ctx["repository"]
                    for key in ("repository", "head_repository")
                ),
                "Invalid branch validation identity.",
            )
            runs[run["id"]] = run
            if run.get("status") in ACTIVE_STATUSES:
                # Preparation can be active before the run joins the reference queue.
                return now
            require(run.get("status") == "completed", "Unknown branch validation status.")
            created = timestamp(run.get("created_at"))
            updated = timestamp(run.get("updated_at"))
            require(created <= updated <= now, "Inconsistent branch validation activity time.")
            # updated_at conservatively retains recent failed, cancelled and rerun attempts.
            # It is an activity time, not a claim about exact job completion.
            latest = max(latest, updated)
        require(len(runs) <= total, "Inconsistent branch validation count.")
        if len(runs) == total:
            return latest
        require(len(data["workflow_runs"]) == 100, "GitHub omitted branch validation runs.")
    raise RecoveryError("Could not read all branch validation history.")


def mutation_allowed(ctx, members, commit_time=None, inactive_hours=None, now=None):
    if pending_work(ctx, members):
        return False
    require((commit_time is None) == (inactive_hours is None), "Incomplete cleanup inactivity threshold.")
    if commit_time is None:
        # Closed PRs and deleted branches retain their orphan policy. The queue still applies.
        return True
    require(
        ctx["ref"].startswith("refs/heads/")
        and type(commit_time) is int
        and commit_time > 0
        and type(inactive_hours) is int
        and inactive_hours >= 0,
        "Invalid branch cleanup inactivity threshold.",
    )
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    latest = branch_activity(ctx, commit_time, now)
    return (now - latest) // 3600 > inactive_hours
