"""Select exact pytest cases from the Porter bundle coverage map."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
E2E_ROOT = REPO_ROOT / "e2e_tests"
CATALOG = E2E_ROOT / "bundle_coverage.json"
REQUEST_FILE = E2E_ROOT / "bundle-validation-request.json"
DEFAULT_REPORT = E2E_ROOT / "bundle-validation.json"
BUNDLE_NAME = re.compile(r"tre-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
REQUEST_STRING_FIELDS = (
    "bundle",
    "marker",
    "processes",
    "requested_checkout_sha",
    "workflow_sha",
    "workflow_ref",
    "ci_ref",
    "tre_id",
    "location",
    "cloud",
    "run_id",
    "run_attempt",
)


def checkout_sha():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def manifest_metadata(filename):
    text = filename.read_text()
    values = {}
    for field in ("name", "version"):
        match = re.search(rf"^{field}:\s*([a-zA-Z0-9.+-]+)\s*$", text, re.MULTILINE)
        if not match:
            raise ValueError(f"Missing plain scalar {field} in {filename.relative_to(REPO_ROOT)}")
        values[field] = match[1]
    return values


def load_catalog():
    catalog = json.loads(CATALOG.read_text())
    if catalog.get("schema_version") != 1:
        raise ValueError("Unsupported bundle coverage schema")
    bundles = catalog["bundles"]
    manifests = {}
    for filename in (REPO_ROOT / "templates").rglob("porter.yaml"):
        metadata = manifest_metadata(filename)
        if metadata["name"] in manifests:
            raise ValueError(f"Duplicate Porter bundle name: {metadata['name']}")
        manifests[metadata["name"]] = (filename, metadata["version"])
    if set(bundles) != set(manifests):
        raise ValueError("Bundle coverage map does not match the current Porter bundle inventory")
    for name, entry in bundles.items():
        filename, version = manifests[name]
        if entry["manifest"] != str(filename.relative_to(REPO_ROOT)):
            raise ValueError(f"Incorrect manifest path for {name}")
        if not set(entry["prerequisites"]) <= bundles.keys():
            raise ValueError(f"Unknown prerequisite for {name}")
        if bool(entry["tests"]) == bool(entry["unavailable_reason"]):
            raise ValueError(f"Declare either executable cases or an unavailable reason for {name}")
        for nodeid in entry["tests"] + entry["related_tests"]:
            if not re.fullmatch(r"test_[a-z0-9_]+\.py::test_[a-z0-9_]+(?:\[[a-zA-Z0-9_-]+\])?", nodeid):
                raise ValueError(f"Invalid explicit pytest node ID for {name}")
            if not (E2E_ROOT / nodeid.split("::")[0]).is_file():
                raise ValueError(f"Missing test module for {name}")
        entry["source_version"] = version
    return bundles


def selection(bundle, marker="", processes="1"):
    bundles = load_catalog()
    if not BUNDLE_NAME.fullmatch(bundle) or bundle not in bundles:
        raise ValueError(f"Unknown bundle identifier: {bundle!r}")
    if marker:
        raise ValueError("Select either a bundle or a marker expression, not both")
    if str(processes) != "1":
        raise ValueError("Per-bundle validation requires exactly one test process")
    entry = bundles[bundle]
    if not entry["tests"]:
        raise ValueError(f"Bundle case is unavailable: {entry['unavailable_reason']}")
    return entry, {name: bundles[name]["source_version"] for name in entry["prerequisites"]}


def request_from_environment(bundle):
    return {
        "bundle": bundle,
        "marker": os.environ.get("TEST_BUNDLE_MARKER", ""),
        "processes": os.environ.get("E2E_TESTS_NUMBER_PROCESSES", "1") or "1",
        "requested_checkout_sha": checkout_sha(),
        "workflow_sha": os.environ.get("GITHUB_WORKFLOW_SHA", ""),
        "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF", ""),
        "ci_ref": os.environ.get("TEST_BUNDLE_CI_REF", ""),
        "tre_id": os.environ.get("TRE_ID", ""),
        "location": os.environ.get("LOCATION", ""),
        "cloud": os.environ.get("AZURE_ENVIRONMENT", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "accept_nexus_eula": os.environ.get("TEST_ACCEPT_NEXUS_EULA", "false").lower() == "true",
    }


def validate_prepared_request(prepared):
    """Require the complete handoff without substituting current-process values."""
    if not isinstance(prepared, dict):
        raise ValueError("A prepared request must be a JSON object")
    for field in (*REQUEST_STRING_FIELDS, "accept_nexus_eula"):
        if field not in prepared:
            raise ValueError(f"Prepared request is missing required field: {field}")
    for field in REQUEST_STRING_FIELDS:
        if not isinstance(prepared[field], str):
            raise ValueError(f"Prepared request field {field} must be a string")
    if type(prepared["accept_nexus_eula"]) is not bool:
        raise ValueError("Nexus consent in a prepared request must be a boolean")
    if not re.fullmatch(r"[0-9a-f]{40}", prepared["requested_checkout_sha"]):
        raise ValueError("Prepared request must contain a full checkout SHA")
    for field in ("tre_id", "location", "cloud"):
        if not prepared[field].strip():
            raise ValueError(f"Prepared request field {field} must not be empty")
    # Unknown fields are excluded from the non-secret evidence report.
    return {field: prepared[field] for field in (*REQUEST_STRING_FIELDS, "accept_nexus_eula")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", default=os.environ.get("TEST_BUNDLE", ""))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--prepare", action="store_true", help="Write the validated CI request for the devcontainer")
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    args.report = args.report.resolve()
    sys.path.insert(0, str(REPO_ROOT))
    from e2e_tests.bundle_evidence import BundleReport, activate

    request = request_from_environment(args.bundle)
    evidence = BundleReport(args.report, {"schema_version": 1, "status": "preflight", "requested_bundle": args.bundle})
    try:
        filename = os.environ.get("TEST_BUNDLE_REQUEST_FILE", "")
        if filename:
            if args.bundle or args.prepare:
                raise ValueError("A prepared request cannot be combined with another bundle selection")
            request = validate_prepared_request(json.loads(Path(filename).read_text()))
            if request["requested_checkout_sha"] != checkout_sha():
                raise ValueError("Prepared request belongs to a different checkout")
            for field, variable in (("tre_id", "TRE_ID"), ("location", "LOCATION"), ("cloud", "AZURE_ENVIRONMENT")):
                if os.environ.get(variable) and request[field] != os.environ[variable]:
                    raise ValueError(f"Prepared request belongs to a different TRE environment ({field})")
        elif args.prepare:
            request = validate_prepared_request(request)
        entry, prerequisites = selection(request["bundle"], request["marker"], request["processes"])
        evidence.data.update(
            requested_bundle=request["bundle"],
            source_bundle_version=entry["source_version"],
            manifest=entry["manifest"],
            requested_tests=entry["tests"],
            declared_prerequisites=prerequisites,
            coverage=entry["coverage"],
            limitations=entry["limitations"],
            provenance=request,
            checkout_sha=checkout_sha(),
        )
        evidence.expected_tests = set(entry["tests"])
        evidence.write()
        if args.prepare:
            REQUEST_FILE.write_text(json.dumps(request, indent=2) + "\n")
        if args.validate_only or args.prepare:
            evidence.data["status"] = "not_run"
            evidence.write()
            print(f"Validated {request['bundle']}: {len(entry['tests'])} explicit test case(s)")
            return 0
        os.environ["TEST_ACCEPT_NEXUS_EULA"] = "true" if request["accept_nexus_eula"] else "false"
        os.chdir(E2E_ROOT)
        sys.path.insert(0, str(E2E_ROOT))
        import pytest
        import config as tre_config

        evidence.data["configured_resource_ids"] = {
            name: getattr(tre_config, name)
            for name in (
                "TEST_WORKSPACE_ID",
                "TEST_WORKSPACE_SERVICE_ID",
                "TEST_AAD_WORKSPACE_ID",
                "TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_ID",
                "TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_SERVICE_ID",
            )
            if getattr(tre_config, name)
        }
        activate(evidence)
        evidence.data["status"] = "collecting" if args.collect_only else "running"
        evidence.write()
        pytest_args = [
            *entry["tests"],
            "-o",
            "addopts=",
            "--junitxml=pytest_e2e_bundle.xml",
            "--verify",
            os.environ.get("IS_API_SECURED", "true"),
        ]
        if args.collect_only:
            pytest_args.append("--collect-only")
        # Ignore inherited addopts: -k, -m or xdist must not alter this exact selection.
        os.environ.pop("PYTEST_ADDOPTS", None)
        exit_code = pytest.main(pytest_args, plugins=[evidence])
        return evidence.finish(exit_code, args.collect_only)
    except (ValueError, OSError, KeyError, TypeError) as error:
        evidence.data.update(status="selection_error", error=str(error), exit_code=2, full_lifecycle_proven=False)
        evidence.write()
        print(f"Bundle validation failed: {error}", file=sys.stderr)
        return 2
    finally:
        activate(None)


if __name__ == "__main__":
    raise SystemExit(main())
