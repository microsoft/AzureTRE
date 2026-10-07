"""Exercise Nexus repository migration through the real configuration script."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
NEXUS = ROOT / "templates/shared_services/sonatype-nexus-vm/scripts"
LINUXVM = ROOT / "templates/workspace_services/guacamole/user_resources/guacamole-azure-linuxvm/terraform"

MOCK_CURL = r"""
import json
import os
from pathlib import Path
import sys

root = Path(os.environ["MOCK_NEXUS_ROOT"])
state_file = root / "state.json"
state = json.loads(state_file.read_text())
args = sys.argv[1:]
url = next(arg for arg in args if arg.startswith("http"))
method = next((arg[2:] for arg in args if arg.startswith("-X") and len(arg) > 2), "GET")
if "-X" in args:
    method = args[args.index("-X") + 1]
state["calls"].append([method, url])


def respond(code=200, body="", exit_code=0):
    state_file.write_text(json.dumps(state))
    if exit_code:
        sys.exit(exit_code)
    if "--fail" in args and code >= 400:
        sys.exit(22)
    if "-o" not in args:
        sys.stdout.write(body)
    if "-w" in args:
        sys.stdout.write(args[args.index("-w") + 1].replace("%{http_code}", str(code)))
    sys.exit(0)


if "/metadata/identity/" in url:
    respond(body='{"access_token":"mock-token"}')
if ".vault.azure.net/" in url:
    respond(body='{"value":"mock-password"}')
if url.endswith("/status"):
    respond()
if url.endswith("/system/eula"):
    respond(body='{"accepted":true}')
if url.endswith("/security/anonymous"):
    respond(body='{"enabled":true}')
if url.endswith("/security/realms/active"):
    respond(204)
if url.endswith("/repositories"):
    state["list_attempts"] += 1
    failures = state["list_failures"]
    if failures:
        failure = failures.pop(0)
        if failure == "connection":
            respond(exit_code=7)
        if failure == "http":
            respond(503, "[]")
        if failure == "invalid-json":
            respond(body="Service unavailable")
        if failure == "invalid-shape":
            respond(body='{"error":"Service unavailable"}')
        if failure == "empty":
            respond()
    respond(body=json.dumps(list(state["repos"].values())))
if "/repositories/" in url:
    parts = url.split("/repositories/", 1)[1].split("/")
    if method == "DELETE":
        if state.get("delete_failures", 0):
            state["delete_failures"] -= 1
            respond(503)
        state["repos"].pop(parts[0], None)
        respond(204)
    if method in ("POST", "PUT"):
        config = json.loads(Path(args[args.index("-d") + 1].removeprefix("@")).read_text())
        name = config["name"]
        existing = state["repos"].get(name)
        if method == "POST" and existing:
            respond(400, "Name is already used")
        if method == "PUT" and (not existing or existing.get("format") != parts[0]):
            respond(404)
        if state.get("create_failures", 0):
            state["create_failures"] -= 1
            respond(503)
        state["repos"][name] = {"name": name, "format": parts[0], "type": parts[1]}
        respond(201 if method == "POST" else 204)
respond(500, "Unexpected request: " + repr(args), exit_code=99)
"""


class NexusRepositoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.script = self.root / "configure_nexus_repos.sh"
        shutil.copy2(NEXUS / self.script.name, self.script)
        self.configs = self.root / "nexus_repos_config"
        self.configs.mkdir()
        self.add_config("ubuntu_proxy_conf.json")
        (self.root / "nexus_realms_config.json").write_text("[]\n")
        binary = self.root / "bin"
        binary.mkdir()
        for name, content in {
            "curl": f"#!{sys.executable}\n" + MOCK_CURL,
            "sleep": "#!/bin/sh\nexit 0\n",
        }.items():
            executable = binary / name
            executable.write_text(content)
            executable.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": str(binary) + os.pathsep + os.environ["PATH"],
            "MOCK_NEXUS_ROOT": str(self.root),
        }
        self.state = {"repos": {}, "list_failures": [], "list_attempts": 0, "calls": []}

    def add_config(self, name):
        shutil.copy2(NEXUS / "nexus_repos_config" / name, self.configs / name)

    def add_repo(self, name="ubuntu", repo_format="apt"):
        self.state["repos"][name] = {"name": name, "format": repo_format, "type": "proxy"}

    def run_script(self):
        state_file = self.root / "state.json"
        state_file.write_text(json.dumps(self.state))
        result = subprocess.run(
            ["/bin/bash", str(self.script), "mock-vault", "mock-identity"],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.state = json.loads(state_file.read_text())
        self.output = result.stdout + result.stderr
        return result

    def mutations(self):
        return [call for call in self.state["calls"] if call[0] != "GET" and "/repositories/" in call[1]]

    def assert_raw_repo(self, name="ubuntu"):
        self.assertEqual(self.state["repos"][name], {"name": name, "format": "raw", "type": "proxy"})

    def test_fresh_install_creates_repository_without_deleting(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, self.output)
        self.assert_raw_repo()
        self.assertEqual([method for method, _ in self.mutations()], ["POST"])

    def test_upgrade_migrates_all_four_apt_repositories(self):
        for config in ("ubuntu_security_proxy_conf.json", "docker_proxy_conf.json", "microsoft_apt_proxy_conf.json"):
            self.add_config(config)
        names = ("ubuntu", "ubuntu-security", "docker", "microsoft-apt")
        for name in names:
            self.add_repo(name)
        result = self.run_script()
        self.assertEqual(result.returncode, 0, self.output)
        for name in names:
            self.assert_raw_repo(name)
        self.assertEqual([method for method, _ in self.mutations()], ["DELETE", "POST"] * 4)

    def test_rerun_updates_raw_repository_without_deleting(self):
        self.add_repo()
        self.assertEqual(self.run_script().returncode, 0, self.output)
        self.state["calls"] = []
        result = self.run_script()
        self.assertEqual(result.returncode, 0, self.output)
        self.assert_raw_repo()
        self.assertEqual([method for method, _ in self.mutations()], ["POST", "PUT"])

    def test_transient_list_failures_retry_before_migration(self):
        for failure in ("connection", "http", "invalid-json", "invalid-shape", "empty"):
            with self.subTest(failure=failure):
                self.add_repo()
                self.state.update(list_failures=[failure], list_attempts=0, calls=[])
                result = self.run_script()
                self.assertEqual(result.returncode, 0, self.output)
                self.assertEqual(self.state["list_attempts"], 2)
                self.assert_raw_repo()
                self.assertEqual([method for method, _ in self.mutations()], ["DELETE", "POST"])

    def test_persistent_list_failures_leave_old_repository_and_fail(self):
        for failure in ("connection", "http", "invalid-json", "invalid-shape", "empty"):
            with self.subTest(failure=failure):
                self.add_repo()
                self.state.update(list_failures=[failure] * 5, list_attempts=0, calls=[])
                result = self.run_script()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.state["list_attempts"], 5)
                self.assertEqual(self.state["repos"]["ubuntu"]["format"], "apt")
                self.assertEqual(self.mutations(), [])
                self.assertIn("Could not remove conflicting repo 'ubuntu'", self.output)

    def test_missing_repository_metadata_fails_without_deletion(self):
        self.state["repos"]["ubuntu"] = {"name": "ubuntu"}
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.mutations(), [])
        self.assertIn("Invalid Nexus repository list", self.output)

    def test_invalid_config_fails_before_repository_requests(self):
        (self.configs / "ubuntu_proxy_conf.json").write_text('{"name":"ubuntu","repoType":"proxy"}\n')
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state["list_attempts"], 0)
        self.assertEqual(self.mutations(), [])
        self.assertIn("Invalid repository configuration", self.output)

    def test_failed_delete_is_retried_before_creation(self):
        self.add_repo()
        self.state["delete_failures"] = 1
        result = self.run_script()
        self.assertEqual(result.returncode, 0, self.output)
        self.assert_raw_repo()
        self.assertEqual([method for method, _ in self.mutations()], ["DELETE", "DELETE", "POST"])

    def test_persistent_delete_failure_fails_without_creation(self):
        self.add_repo()
        self.state["delete_failures"] = 5
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state["repos"]["ubuntu"]["format"], "apt")
        self.assertEqual([method for method, _ in self.mutations()], ["DELETE"] * 5)

    def test_failed_creation_after_deletion_fails_deployment(self):
        self.add_repo()
        self.state["create_failures"] = 5
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("ubuntu", self.state["repos"])
        self.assertIn("Timeout while trying to configure ubuntu", self.output)


class CloudInitWaitTests(unittest.TestCase):
    def test_cloud_init_status_controls_extension_result(self):
        terraform = (LINUXVM / "linuxvm.tf").read_text()
        command = re.search(r'"commandToExecute"\s*:\s*(".*")', terraform).group(1)
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "cloud-init"
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$MOCK_CLOUD_STATUS"\nexit "$MOCK_CLOUD_EXIT"\n')
            executable.chmod(0o755)
            for code, status, expected in [
                (0, "status: done", 0),
                (1, "status: error", 1),
                (2, "status: done", 1),
                (0, "status: running", 1),
            ]:
                with self.subTest(code=code, status=status):
                    result = subprocess.run(
                        ["/bin/sh", "-c", json.loads(command)],
                        env={
                            **os.environ,
                            "PATH": directory + os.pathsep + os.environ["PATH"],
                            "MOCK_CLOUD_STATUS": status,
                            "MOCK_CLOUD_EXIT": str(code),
                        },
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
