"""Plan CI cleanup references and verify their GitHub concurrency ownership."""

import argparse
from datetime import date, datetime, timezone
import json
import os
import re
import subprocess
import sys

from ci_environment_id import ci_tags, environment_prefix, repository_owns, validate_ref
from ci_cleanup_activity import branch_activity, mutation_allowed
from recover_bootstrap_lease import RecoveryError, github, require, verify_concurrency


# Inventory value for a group that another repository tagged. It never equals a Git reference.
FOREIGN_OWNER = "foreign-repository"
# A person sets this tag on a core or management group to keep the environment.
# Scheduled cleanup then does not stop or destroy it. Explicit destruction ignores the tag.
KEEP_TAG = "ci_keep_until"
KEEP_FOREVER = "forever"


def validate_cleanup_ref(ref):
    if ref != "refs/heads/main":
        validate_ref(ref)
    return ref


def verify_account():
    subscription = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
    require(re.fullmatch(r"[A-Za-z0-9-]+", subscription), "The cleanup subscription is unavailable.")
    account = json.loads(subprocess.check_output(["az", "account", "show", "-o", "json"], text=True, timeout=90))
    require(
        isinstance(account, dict)
        and isinstance(account.get("id"), str)
        and account["id"].lower() == subscription.lower(),
        "The cleanup subscription differs.",
    )
    return subscription


def group_tags():
    """Read the tags of every resource group in the cleanup subscription."""
    subscription = verify_account()
    groups = json.loads(
        subprocess.check_output(
            ["az", "group", "list", "--subscription", subscription, "-o", "json"], text=True, timeout=90
        )
    )
    require(isinstance(groups, list), "The cleanup resource group inventory is incomplete.")
    result = {}
    for group in groups:
        require(isinstance(group, dict) and isinstance(group.get("name"), str), "Invalid cleanup resource group.")
        name = group["name"].lower()
        require(
            name not in result
            and isinstance(group.get("id"), str)
            and group["id"].lower() == f"/subscriptions/{subscription}/resourcegroups/{name}".lower(),
            "Inconsistent cleanup resource group identity.",
        )
        require(group.get("tags") is None or isinstance(group.get("tags"), dict), "Invalid cleanup ownership tags.")
        result[name] = ci_tags(group.get("tags"))
    return result


def inventory():
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    return {
        name: tags.get("ci_git_ref") if repository_owns(tags, repository) else FOREIGN_OWNER
        for name, tags in group_tags().items()
    }


def references(groups):
    refs = {"refs/heads/main"}
    prefix = "rg-" + environment_prefix()
    for name, ref in groups.items():
        if not name.startswith(prefix) or ref in (None, FOREIGN_OWNER):
            continue
        require(isinstance(ref, str), "Invalid CI ownership reference.")
        if not ref.startswith(("refs/heads/", "refs/pull/")):
            continue
        validate_cleanup_ref(ref)
        refs.add(ref)
    require(len(refs) <= 256, "Too many cleanup references for one matrix. No cleanup was scheduled.")
    return sorted(refs)


def plan():
    try:
        environment_prefix()
    except ValueError as error:
        # The main workspace sweep uses MAIN_TRE_ID, not the prefix. Keep it for repositories
        # that deploy only main. An invalid prefix that is set is a mistake, so it still fails.
        if os.environ.get("CI_ENV_PREFIX"):
            raise
        # Annotate the run, so that a fork with PR or branch environments sees the skipped cleanup.
        print(
            f"::warning title=CI cleanup scope::{error} Only the main workspace cleanup is scheduled.", file=sys.stderr
        )
        return ["refs/heads/main"]
    return references(inventory())


def context():
    ref = validate_cleanup_ref(os.environ.get("CI_CLEANUP_REF", ""))
    require(os.environ.get("GITHUB_ACTIONS") == "true", "Scoped cleanup requires GitHub Actions concurrency ownership.")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repository), "Invalid cleanup repository.")
    values = [os.environ.get(key, "") for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")]
    require(all(value.isdecimal() and int(value) > 0 for value in values), "The cleanup run identity is unavailable.")
    return {"ref": ref, "repository": repository, "run_id": int(values[0]), "attempt": int(values[1])}


ACTIVE_RUN_STATUSES = frozenset(("in_progress", "queued", "pending", "waiting", "requested"))


def verify_lock(ctx):
    run = github(ctx, f"/actions/runs/{ctx['run_id']}")
    # GitHub reports the whole run as pending while another matrix job waits for
    # its reference group. The job and concurrency owner checks prove this lock.
    require(
        isinstance(run, dict)
        and run.get("id") == ctx["run_id"]
        and run.get("run_attempt") == ctx["attempt"]
        and run.get("status") in ACTIVE_RUN_STATUSES
        and run.get("path") == ".github/workflows/clean_validation_envs.yml"
        and isinstance(run.get("repository"), dict)
        and run["repository"].get("full_name") == ctx["repository"],
        "The cleanup run or attempt does not match.",
    )
    expected_name = os.environ.get("CI_CLEANUP_JOB_NAME", "Clean " + ctx["ref"])
    jobs, total = {}, None
    for page in range(1, 12):
        data = github(ctx, f"/actions/runs/{ctx['run_id']}/attempts/{ctx['attempt']}/jobs?per_page=100&page={page}")
        require(
            isinstance(data, dict)
            and type(data.get("total_count")) is int
            and isinstance(data.get("jobs"), list)
            and 0 <= data["total_count"] <= 1000,
            "Incomplete cleanup jobs response.",
        )
        total = data["total_count"] if total is None else total
        require(total == data["total_count"], "Cleanup jobs changed during verification.")
        for job in data["jobs"]:
            require(
                isinstance(job, dict)
                and type(job.get("id")) is int
                and job["id"] not in jobs
                and isinstance(job.get("name"), str),
                "Invalid cleanup job identity.",
            )
            jobs[job["id"]] = job
        require(len(jobs) <= total, "Inconsistent cleanup job count.")
        if len(jobs) == total:
            break
        require(len(data["jobs"]) == 100, "GitHub omitted cleanup jobs.")
    else:
        raise RecoveryError("Could not verify all cleanup jobs.")
    owners = [job for job in jobs.values() if job["name"] == expected_name and job.get("status") == "in_progress"]
    require(len(owners) == 1, "The current cleanup job is missing or ambiguous.")
    return verify_concurrency(ctx, job_id=owners[0]["id"])


def verify_target(groups, ref, group):
    require(
        ref != "refs/heads/main" and re.fullmatch(rf"rg-{environment_prefix()}[a-z0-9-]+(?:-mgmt)?", group),
        "Invalid isolated cleanup target.",
    )
    core = group.removesuffix("-mgmt")
    siblings = [name for name in (core, core + "-mgmt") if name in groups]
    require(
        siblings and all(groups[name] == ref for name in siblings),
        "Core or management ownership is missing or inconsistent.",
    )


def annotation(text):
    # Escape tag text, so that a value cannot end the annotation or start another workflow command.
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def keep_reason(tags, today):
    """Return why a group's tags keep it, or None. A value that is not valid keeps the group."""
    values = [value for name, value in tags.items() if name.lower() == KEEP_TAG]
    if not values:
        return None
    value = values[0]
    if isinstance(value, str):
        text = value.strip()
        if text.lower() == KEEP_FOREVER:
            return f"{KEEP_TAG} is {KEEP_FOREVER}"
        try:
            until = date.fromisoformat(text) if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text) else None
        except ValueError:
            until = None
        if until is not None:
            # The date is the last day that the cleanup keeps the group.
            return f"{KEEP_TAG} is {text}" if today <= until else None
    return f"{KEEP_TAG} has the invalid value {json.dumps(value)}. Use YYYY-MM-DD or {KEEP_FOREVER}"


def kept(group, today=None):
    """Return why the core or management group of a cleanup target has a keep tag, or None."""
    today = datetime.now(timezone.utc).date() if today is None else today
    tags = group_tags()
    core = group.removesuffix("-mgmt")
    for name in (core, core + "-mgmt"):
        reason = keep_reason(tags.get(name, {}), today)
        if reason:
            return f"{name}: {reason}"
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("plan", "verify-lock", "verify-target", "may-clean", "activity-time"))
    parser.add_argument("--group")
    parser.add_argument("--commit-time", type=int)
    parser.add_argument("--inactive-hours", type=int)
    args = parser.parse_args()
    try:
        if args.operation == "plan":
            print(json.dumps(plan(), separators=(",", ":")))
        else:
            ctx = context()
            members = verify_lock(ctx)
            if args.operation in ("verify-target", "may-clean"):
                verify_target(inventory(), ctx["ref"], args.group or "")
                if args.operation == "may-clean":
                    allowed = mutation_allowed(ctx, members, args.commit_time, args.inactive_hours)
                    # Recheck ownership and queued work after reading history.
                    if allowed:
                        allowed = mutation_allowed(ctx, verify_lock(ctx))
                    # Read the keep tag last, so that a tag added during the checks still applies.
                    reason = kept(args.group.lower()) if allowed else None
                    if reason:
                        print(
                            f"::warning title=CI cleanup keep::Keeping {annotation(reason)}. Cleanup does not stop or destroy it.",
                            file=sys.stderr,
                        )
                    print("keep" if reason else "proceed" if allowed else "defer")
            else:
                verify_account()
                if args.operation == "activity-time":
                    print(int(branch_activity(ctx, args.commit_time)))
    except (RecoveryError, ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"ERROR: CI cleanup refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
