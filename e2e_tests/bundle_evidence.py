"""Write bounded, secret-free evidence for an explicitly selected bundle run."""

import json
from pathlib import Path
from urllib.parse import urlsplit

_ACTIVE_REPORT = None


def activate(report):
    global _ACTIVE_REPORT
    _ACTIVE_REPORT = report


def record_resource(payload, operation, method):
    if _ACTIVE_REPORT is None:
        return
    record = {key: operation[key] for key in ("id", "resourceId", "resourcePath") if key in operation}
    record["method"] = method
    if payload and "templateName" in payload:
        record["bundle"] = payload["templateName"]
    if payload and "templateVersion" in payload:
        record["requested_template_version"] = payload["templateVersion"]
    # Properties and operation messages can contain credentials. Do not copy them.
    _ACTIVE_REPORT.data["resources"].append(record)
    _ACTIVE_REPORT.write()


def record_deployed_resource(resource, resource_path):
    """Record the observed bundle version without copying resource properties."""
    if _ACTIVE_REPORT is None:
        return
    record = {
        "method": "GET",
        "resourceId": resource["id"],
        "resourcePath": resource_path,
        "bundle": resource["templateName"],
        "deployed_template_version": resource["templateVersion"],
    }
    _ACTIVE_REPORT.data["resources"].append(record)
    _ACTIVE_REPORT.write()


def record_reused_resource(resource):
    """Record only the selected prerequisite's identity and deployed version."""
    if _ACTIVE_REPORT is None:
        return
    record = {key: resource[key] for key in ("id", "templateName", "templateVersion") if key in resource}
    if not record.get("id") or not record.get("templateName"):
        raise ValueError("Selected prerequisite is missing its resource identity")
    if record not in _ACTIVE_REPORT.data["reused_resources"]:
        _ACTIVE_REPORT.data["reused_resources"].append(record)
        _ACTIVE_REPORT.write()


def record_operation(endpoint, state, done):
    if _ACTIVE_REPORT is None:
        return
    # Only retain the API path, never a host, token or query string.
    key = urlsplit(endpoint).path
    _ACTIVE_REPORT.data["operations"][key] = {"state": state, "done": done}
    _ACTIVE_REPORT.write()


class BundleReport:
    def __init__(self, filename, data):
        self.filename = Path(filename)
        self.data = {
            **data,
            "full_lifecycle_proven": False,
            "collected_tests": [],
            "test_results": [],
            "resources": [],
            "reused_resources": [],
            "operations": {},
        }
        self.expected_tests = set(data.get("requested_tests", []))
        self.write()

    def write(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.filename.with_suffix(self.filename.suffix + ".tmp")
        temporary.write_text(json.dumps(self.data, indent=2) + "\n")
        temporary.replace(self.filename)

    def pytest_collection_finish(self, session):
        import pytest

        collected = [item.nodeid for item in session.items]
        self.data["collected_tests"] = collected
        self.write()
        if not collected:
            raise pytest.UsageError("Bundle selection collected zero tests")
        if set(collected) != self.expected_tests:
            raise pytest.UsageError("Collected tests do not match the explicit bundle coverage map")

    def pytest_runtest_logreport(self, report):
        result = {
            "nodeid": report.nodeid,
            "phase": report.when,
            "outcome": report.outcome,
            "duration_seconds": report.duration,
        }
        if report.skipped:
            result["reason"] = str(report.longrepr[2]) if isinstance(report.longrepr, tuple) else str(report.longrepr)
        # Failure tracebacks may include request bodies or credentials. Keep them in
        # the existing test logs rather than copying them into the coverage report.
        self.data["test_results"].append(result)
        self.write()

    def finish(self, exit_code, collect_only):
        results = self.data["test_results"]
        calls = [result for result in results if result["phase"] == "call"]
        self.data["counts"] = {
            "passed": sum(result["outcome"] == "passed" for result in calls),
            "failed": sum(result["outcome"] == "failed" for result in calls),
            "errors": sum(result["outcome"] == "failed" and result["phase"] != "call" for result in results),
            "skipped": sum(result["outcome"] == "skipped" for result in results),
        }
        if collect_only:
            state = "not_run" if exit_code == 0 else "collection_failed"
        elif exit_code:
            state = "failed"
        elif not calls or not self.data["counts"]["passed"]:
            state, exit_code = "skipped", 1
        elif self.data["counts"]["skipped"]:
            state = "partial"
        else:
            state = "passed_selected_cases"
        self.data.update(status=state, exit_code=int(exit_code), full_lifecycle_proven=False)
        self.write()
        return int(exit_code)
