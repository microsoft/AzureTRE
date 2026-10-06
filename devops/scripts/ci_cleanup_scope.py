"""Plan CI cleanup references and verify their GitHub concurrency ownership."""

import argparse
import json
import os
import re
import subprocess
import sys

from ci_environment_id import validate_ref
from recover_bootstrap_lease import RecoveryError, github, require, verify_concurrency


def validate_cleanup_ref(ref):
    if ref != "refs/heads/main":
        validate_ref(ref)
    return ref


def verify_account():
    subscription = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
    require(re.fullmatch(r"[A-Za-z0-9-]+", subscription), "The cleanup subscription is unavailable.")
    account = json.loads(subprocess.check_output(["az", "account", "show", "-o", "json"], text=True, timeout=90))
    require(isinstance(account, dict) and isinstance(account.get("id"), str) and account["id"].lower() == subscription.lower(), "The cleanup subscription differs.")
    return subscription


def inventory():
    subscription = verify_account()
    groups = json.loads(subprocess.check_output(["az", "group", "list", "--subscription", subscription, "-o", "json"], text=True, timeout=90))
    require(isinstance(groups, list), "The cleanup resource group inventory is incomplete.")
    result = {}
    for group in groups:
        require(isinstance(group, dict) and isinstance(group.get("name"), str), "Invalid cleanup resource group.")
        name = group["name"].lower()
        require(name not in result and isinstance(group.get("id"), str)
                and group["id"].lower() == f"/subscriptions/{subscription}/resourcegroups/{name}".lower(),
                "Inconsistent cleanup resource group identity.")
        require(group.get("tags") is None or isinstance(group.get("tags"), dict), "Invalid cleanup ownership tags.")
        result[name] = (group.get("tags") or {}).get("ci_git_ref")
    return result


def references(groups):
    refs = {"refs/heads/main"}
    for name, ref in groups.items():
        if not name.startswith("rg-tre") or ref is None:
            continue
        require(isinstance(ref, str), "Invalid CI ownership reference.")
        if not ref.startswith(("refs/heads/", "refs/pull/")):
            continue
        validate_cleanup_ref(ref)
        refs.add(ref)
    require(len(refs) <= 256, "Too many cleanup references for one matrix. No cleanup was scheduled.")
    return sorted(refs)


def context():
    ref = validate_cleanup_ref(os.environ.get("CI_CLEANUP_REF", ""))
    require(os.environ.get("GITHUB_ACTIONS") == "true", "Scoped cleanup requires GitHub Actions concurrency ownership.")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repository), "Invalid cleanup repository.")
    values = [os.environ.get(key, "") for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")]
    require(all(value.isdecimal() and int(value) > 0 for value in values), "The cleanup run identity is unavailable.")
    return {"ref": ref, "repository": repository, "run_id": int(values[0]), "attempt": int(values[1])}


def verify_lock(ctx):
    run = github(ctx, f"/actions/runs/{ctx['run_id']}")
    require(isinstance(run, dict) and run.get("id") == ctx["run_id"] and run.get("run_attempt") == ctx["attempt"]
            and run.get("status") == "in_progress" and run.get("path") == ".github/workflows/clean_validation_envs.yml"
            and isinstance(run.get("repository"), dict) and run["repository"].get("full_name") == ctx["repository"],
            "The cleanup run or attempt does not match.")
    expected_name = os.environ.get("CI_CLEANUP_JOB_NAME", "Clean " + ctx["ref"])
    jobs, total = {}, None
    for page in range(1, 12):
        data = github(ctx, f"/actions/runs/{ctx['run_id']}/attempts/{ctx['attempt']}/jobs?per_page=100&page={page}")
        require(isinstance(data, dict) and type(data.get("total_count")) is int and isinstance(data.get("jobs"), list)
                and 0 <= data["total_count"] <= 1000, "Incomplete cleanup jobs response.")
        total = data["total_count"] if total is None else total
        require(total == data["total_count"], "Cleanup jobs changed during verification.")
        for job in data["jobs"]:
            require(isinstance(job, dict) and type(job.get("id")) is int and job["id"] not in jobs
                    and isinstance(job.get("name"), str), "Invalid cleanup job identity.")
            jobs[job["id"]] = job
        require(len(jobs) <= total, "Inconsistent cleanup job count.")
        if len(jobs) == total:
            break
        require(len(data["jobs"]) == 100, "GitHub omitted cleanup jobs.")
    else:
        raise RecoveryError("Could not verify all cleanup jobs.")
    owners = [job for job in jobs.values() if job["name"] == expected_name and job.get("status") == "in_progress"]
    require(len(owners) == 1, "The current cleanup job is missing or ambiguous.")
    verify_concurrency(ctx, job_id=owners[0]["id"])


def verify_target(groups, ref, group):
    require(ref != "refs/heads/main" and re.fullmatch(r"rg-tre[a-z0-9-]+(?:-mgmt)?", group), "Invalid isolated cleanup target.")
    core = group.removesuffix("-mgmt")
    siblings = [name for name in (core, core + "-mgmt") if name in groups]
    require(siblings and all(groups[name] == ref for name in siblings), "Core or management ownership is missing or inconsistent.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("plan", "verify-lock", "verify-target"))
    parser.add_argument("--group")
    args = parser.parse_args()
    try:
        if args.operation == "plan":
            print(json.dumps(references(inventory()), separators=(",", ":")))
        else:
            ctx = context()
            verify_lock(ctx)
            if args.operation == "verify-target":
                verify_target(inventory(), ctx["ref"], args.group or "")
            else:
                verify_account()
    except (RecoveryError, ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"ERROR: CI cleanup refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
