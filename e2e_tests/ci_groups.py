"""Partition selected E2E cases into serial CI jobs with separate time budgets."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
E2E_ROOT = ROOT / "e2e_tests"
_GROUP = pytest.StashKey[dict]()


def checkout_sha():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def validate_group(group):
    if not isinstance(group, dict) or set(group) != {"name", "checkout_sha", "tests"}:
        raise ValueError("Invalid E2E group request fields")
    if group["name"] not in ("other", "nexus"):
        raise ValueError("Unknown E2E group")
    if group["checkout_sha"] != checkout_sha():
        raise ValueError("E2E group was selected from a different checkout")
    tests = group["tests"]
    if not isinstance(tests, list) or not tests:
        raise ValueError("E2E group must contain explicit test cases")
    if any(
        not isinstance(nodeid, str) or not re.match(r"^(?:[a-zA-Z0-9_]+/)*test_[a-zA-Z0-9_]+\.py::", nodeid)
        for nodeid in tests
    ):
        raise ValueError("Invalid E2E test case")
    if group["name"] == "nexus" and len(tests) != 1:
        raise ValueError("Each Nexus job must contain exactly one case")
    if len(tests) != len(set(tests)):
        raise ValueError("Duplicate E2E test cases")
    return group


def plan(selector):
    if not selector.strip():
        raise ValueError("An E2E marker selection is required")
    groups = {"other": [], "nexus": []}

    class CollectGroups:
        def pytest_collection_finish(self, session):
            for item in session.items:
                name = "nexus" if item.get_closest_marker("nexus") is not None else "other"
                groups[name].append(item.nodeid)

    code = pytest.main(["--collect-only", "-q", "-o", "addopts=", "-m", selector], plugins=[CollectGroups()])
    if code != 0:
        raise ValueError(f"E2E selection failed with pytest exit code {code}")
    if not any(groups.values()):
        raise ValueError("E2E selection contains no cases")
    revision = checkout_sha()
    return [
        validate_group({"name": name, "checkout_sha": revision, "tests": tests})
        for name, tests in groups.items()
        if tests
    ]


def pytest_configure(config):
    # Loading this module with -p registers the guard in xdist workers too.
    try:
        group = validate_group(json.loads(Path(os.environ["E2E_CI_GROUP_FILE"]).read_text()))
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise pytest.UsageError(str(error)) from error
    config.stash[_GROUP] = group


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    group = config.stash[_GROUP]
    if {item.nodeid for item in items} != set(group["tests"]):
        raise pytest.UsageError("Collected E2E cases differ from the planned group")
    if any((item.get_closest_marker("nexus") is not None) != (group["name"] == "nexus") for item in items):
        raise pytest.UsageError("Nexus must run separately from the other E2E cases")


def run(filename):
    group = validate_group(json.loads(filename.read_text()))
    os.environ["E2E_CI_GROUP_FILE"] = str(filename)
    processes = 1 if group["name"] == "nexus" else int(os.environ.get("E2E_TESTS_NUMBER_PROCESSES") or "1")
    if processes < 0:
        raise ValueError("E2E process count must not be negative")
    args = ["-p", "e2e_tests.ci_groups", "-o", "addopts=", "--verify", os.environ.get("IS_API_SECURED", "true")]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(E2E_ROOT), environment.get("PYTHONPATH", "")))
    # Check in the controller before xdist starts workers. A worker collection
    # error can otherwise lose its useful diagnostic in xdist's error handling.
    validation = subprocess.run(
        [sys.executable, "-m", "pytest", *args, "--collect-only", "-q", *group["tests"]],
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if validation.returncode != 0:
        print(validation.stdout, end="")
        print(validation.stderr, end="", file=sys.stderr)
        return validation.returncode
    args.extend(["--junit-xml", f"pytest_e2e_{group['name']}.xml", *group["tests"]])
    if processes > 1:
        args.extend(["-n", str(processes)])
    return int(pytest.main(args))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--run", type=Path)
    args = parser.parse_args()
    if args.run is not None:
        args.run = args.run.resolve()
    os.chdir(E2E_ROOT)
    sys.path[:0] = [str(ROOT), str(E2E_ROOT)]
    os.environ.pop("PYTEST_ADDOPTS", None)
    try:
        if args.plan:
            groups = plan(os.environ.get("E2E_SELECTOR", ""))
            with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
                output.write("groups=" + json.dumps(groups, separators=(",", ":")) + "\n")
            return 0
        return run(args.run)
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(f"E2E group validation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
