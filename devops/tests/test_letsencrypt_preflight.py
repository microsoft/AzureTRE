"""Check certificate preflight ordering through the real Make target and script."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class LetsEncryptPreflightTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for relative in [
            "Makefile",
            "core/terraform/scripts/letsencrypt.sh",
            "core/terraform/scripts/validate_certbot.sh",
        ]:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)

        self.log = self.root / "calls.log"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.certbot = self.bin / "certbot with spaces"
        self.certbot.write_text("#!/bin/bash\nexit 0\n")
        self.certbot.chmod(0o755)
        self.env = {
            "PATH": str(self.bin) + os.pathsep + os.defpath,
            "CALL_LOG": str(self.log),
            "CERTBOT_BIN": str(self.certbot),
            "STORAGE_ACCOUNT": "mockstorage",
            "KEYVAULT": "",
        }
        for command in ["az", "terraform"]:
            stub = self.bin / command
            stub.write_text('#!/bin/bash\nprintf "unexpected command\\n" >> "$CALL_LOG"\nexit 90\n')
            stub.chmod(0o755)

        scripts = self.root / "devops/scripts"
        scripts.mkdir(parents=True)
        (scripts / "bootstrap_azure_env.sh").write_text('printf "bootstrap\\n" >> "$CALL_LOG"\n')
        (scripts / "load_env.sh").write_text('set -a\n. "$1"\nset +a\n')
        # Stop at the first certificate Azure operation, without contacting Azure.
        (scripts / "storage_enable_public_access.sh").write_text(
            'printf "certificate-azure\\n" >> "$CALL_LOG"\n'
            'printf "Reached mocked certificate operations\\n" >&2\n'
            "exit 73\n"
        )
        self.set_outputs("rg-from-terraform")

    def set_outputs(self, resource_group):
        value = "" if resource_group is None else f"RESOURCE_GROUP_NAME={resource_group}\\n"
        (self.root / "core/terraform/outputs.sh").write_text(
            f'printf "outputs\\n" >> "$CALL_LOG"\nprintf \'{value}\' > ../private.env\n'
        )

    def run_command(self, command):
        self.log.unlink(missing_ok=True)
        result = subprocess.run(
            command,
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        self.assertNotIn("unexpected command", calls)
        return result, calls

    def run_make(self):
        return self.run_command([shutil.which("make"), "--no-print-directory", "letsencrypt"])

    def run_script(self):
        return self.run_command(["/bin/bash", "core/terraform/scripts/letsencrypt.sh"])

    def test_make_invalid_certbot_stops_before_azure_preparation(self):
        non_executable = self.root / "non-executable"
        non_executable.write_text("not executable\n")
        for value in [str(self.root / "missing"), "missing-certbot", str(non_executable), str(self.bin), "true"]:
            with self.subTest(certbot=value):
                self.env["CERTBOT_BIN"] = value
                result, calls = self.run_make()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Set CERTBOT_BIN to a valid executable path", result.stderr)
                self.assertEqual(calls, [])

    def test_make_valid_certbot_loads_resource_group_from_outputs(self):
        for value in [str(self.certbot), self.certbot.name, "./bin/" + self.certbot.name]:
            with self.subTest(certbot=value):
                self.env["CERTBOT_BIN"] = value
                result, calls = self.run_make()
                self.assertIn("Reached mocked certificate operations", result.stderr)
                self.assertEqual(calls, ["bootstrap", "outputs", "certificate-azure"])

    def test_make_missing_resource_group_stops_certificate_operations(self):
        for resource_group in [None, ""]:
            with self.subTest(resource_group=resource_group):
                self.set_outputs(resource_group)
                result, calls = self.run_make()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("RESOURCE_GROUP_NAME not set", result.stderr)
                self.assertEqual(calls, ["bootstrap", "outputs"])

    def test_direct_script_invalid_certbot_stops_before_operations(self):
        self.env["CERTBOT_BIN"] = str(self.root / "missing")
        result, calls = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Set CERTBOT_BIN to a valid executable path", result.stderr)
        self.assertEqual(calls, [])

    def test_direct_script_missing_resource_group_stops_before_operations(self):
        for resource_group in [None, ""]:
            with self.subTest(resource_group=resource_group):
                if resource_group is None:
                    self.env.pop("RESOURCE_GROUP_NAME", None)
                else:
                    self.env["RESOURCE_GROUP_NAME"] = resource_group
                result, calls = self.run_script()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("RESOURCE_GROUP_NAME not set", result.stderr)
                self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
