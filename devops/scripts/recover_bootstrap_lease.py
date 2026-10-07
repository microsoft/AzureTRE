"""Recover only an empty, unowned bootstrap lease in an isolated PR CI backend."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request
from urllib.parse import quote

from ci_environment_id import environment_id


class RecoveryError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise RecoveryError(message)


def context():
    env = os.environ
    require(env.get("CI_BOOTSTRAP_LEASE_RECOVERY") == "true" and env.get("GITHUB_ACTIONS") == "true",
            "Bootstrap lease recovery is enabled only in PR GitHub Actions jobs.")
    ref = env.get("TF_VAR_ci_git_ref", "")
    match = re.fullmatch(r"refs/pull/([1-9][0-9]*)/merge", ref)
    require(match is not None and match[1] == env.get("CI_RECOVERY_PR_NUMBER"), "The PR ownership reference does not match the event.")
    repository = env.get("GITHUB_REPOSITORY", "")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repository)
            and repository.split("/")[-1] not in (".", ".."), "The GitHub repository is invalid.")
    run_id = env.get("GITHUB_RUN_ID", "")
    attempt = env.get("GITHUB_RUN_ATTEMPT", "")
    require(run_id.isdecimal() and int(run_id) > 0 and attempt.isdecimal() and int(attempt) > 0, "The workflow run identity is missing.")
    ref_id = hashlib.sha512((ref + "\n").encode()).hexdigest()[:8]
    regional_id = env.get("CI_ENVIRONMENT_ID", "")
    if regional_id:
        try:
            ref_id = environment_id(ref, env.get("TF_VAR_location", ""), env.get("AZURE_ENVIRONMENT", ""))
        except ValueError as error:
            raise RecoveryError(str(error)) from error
        require(regional_id == ref_id, "The regional CI environment identity does not match.")
    group = "rg-tre" + ref_id + "-mgmt"
    account = "tre" + ref_id + "mgmt"
    require(env.get("TF_VAR_mgmt_resource_group_name") == group and env.get("TF_VAR_mgmt_storage_account_name") == account,
            "The management account is not the expected isolated PR backend.")
    subscription = env.get("ARM_SUBSCRIPTION_ID", "")
    require(re.fullmatch(r"[A-Za-z0-9-]+", subscription), "The Azure subscription is missing or invalid.")
    container = env.get("TF_VAR_terraform_state_container_name", "")
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", container), "The state container is invalid.")
    return {"ref": ref, "repository": repository, "run_id": int(run_id), "attempt": int(attempt),
            "group": group, "account": account, "subscription": subscription, "container": container}


def azure(ctx, *args):
    result = subprocess.run(["az", *args, "--subscription", ctx["subscription"], "--only-show-errors", "--output", "json"],
                            capture_output=True, text=True, timeout=90)
    require(result.returncode == 0, "Azure " + " ".join(args[:3]) + " failed: " + result.stderr.strip())
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        raise RecoveryError("Azure returned invalid JSON.") from error


def verify_owner(ctx):
    group = azure(ctx, "group", "show", "--name", ctx["group"])
    expected = f"/subscriptions/{ctx['subscription']}/resourceGroups/{ctx['group']}"
    require(isinstance(group, dict) and isinstance(group.get("id"), str) and group["id"].lower() == expected.lower(),
            "The management resource group identity does not match.")
    require(isinstance(group.get("tags"), dict) and group["tags"].get("ci_git_ref") == ctx["ref"],
            "The management resource group is not tagged for this PR.")


def github(ctx, suffix):
    # Recovery receives the deployment job token only for the PR bootstrap command.
    # Cleanup supplies GITHUB_TOKEN. Both jobs grant actions: read. Anonymous reads
    # share a small per-address rate limit and fail for private forks.
    token = os.environ.get("CI_RECOVERY_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    require(token, "A GitHub token with actions: read is unavailable. Workflow ownership is unverified.")
    request = urllib.request.Request("https://api.github.com/repos/" + ctx["repository"] + suffix,
                                     headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10",
                                              "User-Agent": "AzureTRE-bootstrap-lease-recovery",
                                              "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, ValueError) as error:
        raise RecoveryError("Could not verify workflow activity. No lease will be broken.") from error


# These workflows have no path to an isolated CI Terraform backend. Verify their
# immutable source before treating an active run as unrelated, not their title.
READ_ONLY_WORKFLOWS = frozenset((
    "build_validation_develop.yml", "build_docker_images.yml", "build_all_dockerfiles.yml",
    "build_docs.yml", "codeql-analysis.yml", "e2e_helper_tests.yml", "flag_external_pr.yml", "resource_processor_tests.yml",
    "test_results.yml",
))
GITHUB_MANAGED_READ_ONLY_WORKFLOWS = frozenset((
    "dynamic/agents/copilot-pull-request-reviewer",
    "dynamic/github-code-quality/codeql",
    "dynamic/github-code-scanning/codeql",
    "dynamic/pages/pages-build-deployment",
))
WRITER_WORKFLOWS = frozenset(("pr_comment_bot.yml", "deploy_tre.yml", "deploy_tre_branch.yml", "clean_validation_envs.yml"))
SOURCE = Path(__file__).resolve().parents[2]


def verify_source(ctx, path, sha, cache):
    require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha), "The workflow source commit is unavailable.")
    key = (path, sha)
    if key not in cache:
        content = (SOURCE / path).read_bytes()
        expected = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        actual = github(ctx, f"/contents/{path}?ref={sha}")
        require(isinstance(actual, dict) and actual.get("type") == "file" and actual.get("sha") == expected,
                f"Workflow source {path}@{sha} differs from the audited checkout. Exclusive access is unverified.")
        cache.add(key)


def verify_concurrency(ctx, job_id=None):
    """Prove that GitHub holds the reference lock for this exact run or job.

    Read the complete, non-paginated group. The filtered endpoint currently
    returns 422 for some reusable-workflow owners that the full response lists.
    Queued successors cannot acquire the lock until the current owner releases it.
    """
    group = "deploy-" + ctx["ref"]
    data = github(ctx, f"/actions/concurrency_groups/{quote(group, safe='')}")
    target = f"{ctx.get('subscription', '?')}/{ctx.get('account', '?')}/{ctx.get('container', '?')}; {ctx['ref']}"
    require(isinstance(data, dict) and isinstance(data.get("group_name"), str) and data["group_name"].lower() == group.lower()
            and type(data.get("total_count")) is int and isinstance(data.get("group_members"), list),
            f"Incomplete concurrency ownership for {target}.")
    members = data["group_members"]
    require(data["total_count"] == len(members) and 1 <= len(members) <= 101,
            f"Incomplete concurrency queue for {group}; target={target}.")
    seen = set()
    for member in members:
        require(isinstance(member, dict) and type(member.get("run_id")) is int and member["run_id"] > 0
                and member.get("status") in ("in_progress", "pending")
                and ("job_id" not in member or type(member["job_id"]) is int and member["job_id"] > 0),
                f"Invalid concurrency member for {group}; target={target}.")
        identity = (member["run_id"], member.get("job_id"))
        require(identity not in seen, f"Duplicate concurrency ownership for {group}; target={target}.")
        seen.add(identity)
    owners = [member for member in members if member["status"] == "in_progress"]
    require(len(owners) == 1, f"Missing or ambiguous concurrency owner for {group}; target={target}.")
    owner = owners[0]
    require(owner["run_id"] == ctx["run_id"] and (job_id is None or owner.get("job_id") == job_id),
            f"Concurrency owner run={owner['run_id']} job={owner.get('job_id')} workflow={owner.get('run_name', '?')} "
            f"state={owner['status']} does not match run {ctx['run_id']} for {target}.")
    if job_id is None and "job_id" in owner:
        job = github(ctx, f"/actions/jobs/{owner['job_id']}")
        require(isinstance(job, dict) and job.get("id") == owner["job_id"] and job.get("run_id") == ctx["run_id"]
                and job.get("run_attempt") == ctx["attempt"] and job.get("status") == "in_progress"
                and job.get("name") == "Deploy PR / Deploy Management",
                f"The concurrency job is not this recovery attempt's management deployment; target={target}.")


def verify_workflows(ctx, cache=None):
    cache = set() if cache is None else cache
    current = github(ctx, f"/actions/runs/{ctx['run_id']}")
    require(isinstance(current, dict) and current.get("id") == ctx["run_id"] and current.get("run_attempt") == ctx["attempt"]
            and current.get("status") == "in_progress" and current.get("event") == "issue_comment"
            and current.get("path") == ".github/workflows/pr_comment_bot.yml"
            and isinstance(current.get("repository"), dict) and current["repository"].get("full_name") == ctx["repository"],
            "The current run is not an active PR comment workflow.")
    workflow_prefix = ctx["repository"] + "/.github/workflows/deploy_tre_reusable.yml@"
    workflows = current.get("referenced_workflows")
    deployments = [item for item in workflows if isinstance(item, dict) and isinstance(item.get("path"), str)
                   and item["path"].startswith(workflow_prefix)] if isinstance(workflows, list) else []
    require(len(deployments) == 1, "The PR deployment workflow source is unavailable or ambiguous.")
    require(deployments[0].get("sha") == current.get("head_sha"), "Caller and deployment workflow sources differ.")
    trusted = deployments[0].get("sha")
    # A /test run using pre-fix workflow wiring must not enable the weaker guard.
    for name in ("pr_comment_bot.yml", "deploy_tre_reusable.yml", "clean_validation_envs.yml"):
        verify_source(ctx, ".github/workflows/" + name, trusted, cache)
    verify_concurrency(ctx)
    for status in ("requested", "waiting", "pending", "queued", "in_progress"):
        seen = set()
        total = None
        for page in range(1, 12):
            data = github(ctx, f"/actions/runs?status={status}&per_page=100&page={page}")
            require(isinstance(data, dict) and type(data.get("total_count")) is int and isinstance(data.get("workflow_runs"), list),
                    "GitHub returned incomplete workflow activity.")
            require(0 <= data["total_count"] <= 1000, "The workflow activity list is too large to verify.")
            total = data["total_count"] if total is None else total
            require(total == data["total_count"], "Workflow activity changed during verification.")
            for run in data["workflow_runs"]:
                require(isinstance(run, dict) and type(run.get("id")) is int and run["id"] > 0 and run["id"] not in seen,
                        "GitHub returned invalid workflow ownership data.")
                seen.add(run["id"])
                if run["id"] == ctx["run_id"]:
                    continue
                try:
                    verify_other_run(ctx, run, cache, trusted)
                except RecoveryError as error:
                    raise RecoveryError(f"Run {run['id']} workflow={run.get('path', '?')} state={status} "
                                        f"target=unverified may affect {ctx['ref']}: {error}") from error
            require(len(seen) <= total, "GitHub returned inconsistent workflow activity.")
            if len(seen) == total:
                break
            require(len(data["workflow_runs"]) == 100, "GitHub omitted workflow activity.")
        else:
            raise RecoveryError("Could not verify all workflow activity.")
        if status == "in_progress":
            require(ctx["run_id"] in seen, "GitHub omitted the active recovery run.")
    # Activity classification finds legacy or unknown writers. The concurrency
    # lock, held for the entire deployment, excludes new conforming writers.
    verify_concurrency(ctx)


def verify_other_run(ctx, run, cache, trusted):
    path = run.get("path", "")
    # GitHub supplies these dynamic workflow identities. They are not display
    # titles or comment inputs, and cannot run the Azure deployment workflows.
    if path in GITHUB_MANAGED_READ_ONLY_WORKFLOWS and run.get("event") == "dynamic":
        return
    require(isinstance(path, str) and path.startswith(".github/workflows/"), "Unknown workflow identity.")
    name = path.removeprefix(".github/workflows/")
    require(name in READ_ONLY_WORKFLOWS | WRITER_WORKFLOWS, "Workflow backend ownership is unavailable.")
    # The default-branch caller commit is the audited baseline, not the PR checkout.
    # If a PR changes an allow-listed workflow, its active runs remain unclassified.
    verify_source(ctx, path, trusted, cache)
    verify_source(ctx, path, run.get("head_sha"), cache)
    if name in WRITER_WORKFLOWS:
        # These audited entry points bind their mutation targets to deploy-<ref>.
        # A queued same-reference operation will wait; different references do
        # not share a backend. No inference from issue_comment head_branch.
        verify_source(ctx, ".github/workflows/deploy_tre_reusable.yml", run.get("head_sha"), cache)


def blob(ctx, operation, *args):
    return azure(ctx, "storage", "blob", *operation, "--account-name", ctx["account"], "--container-name", ctx["container"],
                 "--auth-mode", "login", *args)


def snapshot(value):
    require(isinstance(value, dict) and value.get("name") == "bootstrap.tfstate", "The bootstrap blob identity does not match.")
    properties = value.get("properties")
    metadata = value.get("metadata")
    require(isinstance(properties, dict) and isinstance(metadata, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()),
            "The bootstrap blob properties are incomplete.")
    require(type(properties.get("contentLength")) is int and properties["contentLength"] == 0, "Populated bootstrap state requires manual recovery.")
    require(properties.get("blobType") == "BlockBlob", "The bootstrap blob type is unexpected.")
    require(not any(key.lower() == "terraformlockid" and item for key, item in metadata.items()), "Terraform lock metadata requires manual recovery.")
    require(isinstance(properties.get("etag"), str) and properties["etag"] and isinstance(properties.get("lastModified"), str)
            and properties["lastModified"], "The bootstrap blob version is missing.")
    require(isinstance(properties.get("lease"), dict), "The bootstrap lease properties are missing.")
    return {"name": value["name"], "metadata": metadata,
            **{key: properties[key] for key in ("contentLength", "blobType", "etag", "lastModified")}}


def require_orphan(value):
    result = snapshot(value)
    require(value["properties"]["lease"] == {"duration": "infinite", "state": "leased", "status": "locked"},
            "Only an infinite, locked bootstrap lease can be recovered automatically.")
    return result


def recover(ctx):
    verify_owner(ctx)
    account = azure(ctx, "storage", "account", "show", "--resource-group", ctx["group"], "--name", ctx["account"])
    expected = f"/subscriptions/{ctx['subscription']}/resourceGroups/{ctx['group']}/providers/Microsoft.Storage/storageAccounts/{ctx['account']}"
    require(isinstance(account, dict) and isinstance(account.get("id"), str) and account["id"].lower() == expected.lower(),
            "The storage account identity does not match.")
    exists = blob(ctx, ["exists"], "--name", "bootstrap.tfstate")
    require(isinstance(exists, dict) and type(exists.get("exists")) is bool, "The bootstrap blob existence check is incomplete.")
    if not exists["exists"]:
        print("Bootstrap state does not exist. No lease recovery is needed.")
        return
    initial = blob(ctx, ["show"], "--name", "bootstrap.tfstate")
    require(isinstance(initial, dict) and isinstance(initial.get("properties"), dict)
            and isinstance(initial["properties"].get("lease"), dict), "The bootstrap lease properties are incomplete.")
    if initial["properties"]["lease"].get("status") == "unlocked":
        print("Bootstrap state is unlocked. No lease recovery is needed.")
        return
    before = require_orphan(initial)
    cache = set()
    verify_workflows(ctx, cache)
    print("Eligible empty bootstrap lease found under the verified deployment concurrency lock.", flush=True)
    verify_owner(ctx)
    current = blob(ctx, ["show"], "--name", "bootstrap.tfstate")
    require(require_orphan(current) == before, "The bootstrap blob changed. No lease will be broken.")
    verify_workflows(ctx, cache)
    # The shared per-reference deployment concurrency group excludes other Terraform
    # writers. If-Match additionally rejects intervening content/metadata changes.
    # Lease operations do not change ETag or Last-Modified, so age is not ownership proof.
    print("Breaking the abandoned empty bootstrap lease once. Preserving blob content and metadata.", flush=True)
    blob(ctx, ["lease", "break"], "--blob-name", "bootstrap.tfstate", "--lease-break-period", "0", "--if-match", before["etag"])
    after = blob(ctx, ["show"], "--name", "bootstrap.tfstate")
    require(snapshot(after) == before, "Bootstrap blob content or metadata changed during recovery. Terraform will not start.")
    require(after["properties"]["lease"].get("status") == "unlocked"
            and after["properties"]["lease"].get("state") in ("available", "broken"), "The bootstrap lease is still locked. Terraform will not start.")
    print("Bootstrap lease recovery verified. Terraform initialisation can proceed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("context", "verify-owner", "recover"))
    args = parser.parse_args()
    try:
        ctx = context()
        if args.operation == "verify-owner":
            verify_owner(ctx)
        elif args.operation == "recover":
            recover(ctx)
    except (RecoveryError, OSError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: Bootstrap lease recovery refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
