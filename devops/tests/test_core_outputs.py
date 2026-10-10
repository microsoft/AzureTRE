"""Exercise core output failures through the real UI Make target, without Azure."""

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")
OUTPUT_NAMES = re.findall(r'^output "([^"]+)"', (ROOT / "core/terraform/outputs.tf").read_text(), re.MULTILINE)
VALID_OUTPUT = json.dumps(
    {
        name: {"value": "mockstorage" if name == "static_web_storage" else f"mock-{name}", "type": "string"}
        for name in OUTPUT_NAMES
    }
)
AUXILIARY_OUTPUTS = {
    "WORKSPACE_API_CLIENT_ID": ("TEST_WORKSPACE_APP_ID",),
    "WORKSPACE_API_CLIENT_SECRET": ("TEST_WORKSPACE_APP_SECRET",),
    "SUB_ID": ("SUBSCRIPTION_ID", "AZURE_SUBSCRIPTION_ID"),
    "TENANT_ID": ("AZURE_TENANT_ID",),
}


class CoreOutputTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for relative in (
            "Makefile",
            "config_schema.json",
            "core/terraform/outputs.sh",
            "core/terraform/json-to-env.sh",
            "devops/scripts/load_env.sh",
            "devops/scripts/load_and_validate_env.sh",
            "devops/scripts/construct_tre_url.sh",
            "devops/scripts/convert_azure_env_to_arm_env.sh",
        ):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        self.core = self.root / "core"
        self.log = self.root / "calls.log"
        scripts = self.root / "devops/scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        (scripts / "bootstrap_azure_env.sh").write_text("true\n")
        (scripts / "storage_enable_public_access.sh").write_text(
            'echo storage-enable >> "$CALL_LOG"\ntrap \'echo storage-disable >> "$CALL_LOG"\' EXIT\n'
        )
        deploy = scripts / "build_deploy_ui.sh"
        deploy.write_text('#!/bin/bash\necho "ui:$STORAGE_ACCOUNT" >> "$CALL_LOG"\n')
        deploy.chmod(0o755)
        mock = self.root / "bin"
        mock.mkdir()
        terraform = mock / "terraform"
        terraform.write_text(
            '#!/bin/bash\necho "terraform:$1" >> "$CALL_LOG"\n'
            'if [ "$1" = init ]; then exit "${INIT_EXIT:-0}"; fi\n'
            'printf "%s" "$OUTPUT_JSON"\n'
            'if [ "${OUTPUT_EXIT:-0}" != 0 ]; then echo "Failed to load state" >&2; fi\n'
            'exit "${OUTPUT_EXIT:-0}"\n'
        )
        terraform.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": str(mock) + os.pathsep + os.environ["PATH"],
            "CALL_LOG": str(self.log),
            "OUTPUT_JSON": VALID_OUTPUT,
            "INIT_EXIT": "0",
            "OUTPUT_EXIT": "0",
            "DEPLOY_UI": "true",
            **dict.fromkeys(AUXILIARY_OUTPUTS, ""),
        }
        self.private = self.core / "private.env"
        self.private.write_text("EXISTING='keep me'\n")
        self.cache = self.core / "tre_output.json"

    def run_make(self):
        result = subprocess.run(
            [shutil.which("make"), "--no-print-directory", f"SHELL={BASH}", "build-and-deploy-ui"],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.calls = self.log.read_text().splitlines()
        self.assertEqual(self.calls[-1], "storage-disable")
        self.assertEqual(list(self.core.glob("*.tmp.*")), [])
        return result

    def assert_stopped(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(any(call.startswith("ui:") for call in self.calls))
        self.assertEqual(self.private.read_text(), "EXISTING='keep me'\n")

    def test_failed_init_stops_before_output_and_ui(self):
        self.env["INIT_EXIT"] = "17"
        result = self.run_make()
        self.assert_stopped(result)
        self.assertNotIn("terraform:output", self.calls)
        self.assertFalse(self.cache.exists())
        self.assertIn("Error 17", result.stderr)

    def test_failed_output_stops_ui_and_does_not_cache_partial_output(self):
        for output in ("", '{"partial":', VALID_OUTPUT):
            with self.subTest(output=output):
                self.env.update(OUTPUT_EXIT="23", OUTPUT_JSON=output)
                result = self.run_make()
                self.assert_stopped(result)
                self.assertFalse(self.cache.exists())
                self.assertIn("Failed to load state", result.stderr)
                self.assertIn("Error 23", result.stderr)

    def test_invalid_successful_output_is_not_cached(self):
        for output in ("", "{}", "[]", "null", '{"partial":'):
            with self.subTest(output=output):
                self.env["OUTPUT_JSON"] = output
                result = self.run_make()
                self.assert_stopped(result)
                self.assertFalse(self.cache.exists())

    def test_invalid_nonempty_cache_stops_ui(self):
        self.cache.write_text('{"partial":')
        result = self.run_make()
        self.assert_stopped(result)
        self.assertNotIn("terraform:output", self.calls)

    def test_incomplete_outputs_are_not_published(self):
        incomplete_outputs = [{"unexpected": {"value": "x"}}, {"static_web_storage": {"value": "mockstorage"}}]
        for missing in ("static_web_storage", "core_resource_group_name", "keyvault_name"):
            output = json.loads(VALID_OUTPUT)
            del output[missing]
            incomplete_outputs.append(output)
        for output in incomplete_outputs:
            with self.subTest(output=output):
                self.env["OUTPUT_JSON"] = json.dumps(output)
                self.assert_stopped(self.run_make())
                self.assertFalse(self.cache.exists())

    def test_invalid_mapped_values_are_not_published(self):
        for value in (
            None,
            "",
            " \t\n",
            "mock\nstorage",
            "mock\rstorage",
            "mock\x00storage",
            "mock'storage",
            1,
            False,
            [],
            {},
        ):
            with self.subTest(value=value):
                output = json.loads(VALID_OUTPUT)
                output["static_web_storage"]["value"] = value
                self.env["OUTPUT_JSON"] = json.dumps(output)
                self.assert_stopped(self.run_make())
                self.assertFalse(self.cache.exists())

    def test_missing_output_value_is_not_published(self):
        output = json.loads(VALID_OUTPUT)
        output["static_web_storage"] = {"type": "string"}
        self.env["OUTPUT_JSON"] = json.dumps(output)
        self.assert_stopped(self.run_make())
        self.assertFalse(self.cache.exists())

    def test_invalid_auxiliary_values_preserve_existing_files(self):
        marker = self.root / "injected"
        invalid_values = ("mock'secret", "mock\nsecret", "mock\rsecret", f"secret'; touch {marker}; #")
        for source_name in AUXILIARY_OUTPUTS:
            for value in invalid_values:
                for cached in (False, True):
                    with self.subTest(source_name=source_name, value=value, cached=cached):
                        self.env[source_name] = value
                        if cached:
                            self.cache.write_text(VALID_OUTPUT)
                        else:
                            self.cache.unlink(missing_ok=True)
                        result = self.run_make()
                        self.assert_stopped(result)
                        self.assertIn(source_name, result.stderr)
                        self.assertNotIn(value, result.stdout + result.stderr)
                        self.assertFalse(marker.exists())
                        if cached:
                            self.assertEqual(self.cache.read_text(), VALID_OUTPUT)
                        else:
                            self.assertFalse(self.cache.exists())
            self.env[source_name] = ""

    def test_auxiliary_values_from_core_env_are_validated(self):
        value = "mock'secret"
        (self.core / ".env").write_text(f"WORKSPACE_API_CLIENT_SECRET={shlex.quote(value)}\n")
        self.assert_stopped(self.run_make())
        self.assertFalse(self.cache.exists())

    @unittest.skipUnless(shutil.which("pajv"), "The development container provides pajv for config validation")
    def test_config_rejects_unsupported_secrets_before_shell_export(self):
        config = {
            "location": "westeurope",
            "tre_id": "mocktre",
            "authentication": {
                "aad_tenant_id": "00000000-0000-0000-0000-000000000000",
                "workspace_api_client_secret": "mock-safe-secret",
            },
        }
        config_file = self.root / "config.yaml"
        config_file.write_text(json.dumps(config))
        valid = subprocess.run(
            [shutil.which("pajv"), "validate", "-s", "config_schema.json", "-d", "config.yaml"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        yq = self.root / "bin/yq"
        yq.write_text('#!/bin/bash\necho yq >> "$CALL_LOG"\nexit 97\n')
        yq.chmod(0o755)
        for character in ("'", "\r", "\n", "\x00"):
            for value in (f"mock{character}secret-value", f"mock-secret-value{character}"):
                with self.subTest(value=value):
                    config["authentication"]["workspace_api_client_secret"] = value
                    config_file.write_text(json.dumps(config))
                    result = subprocess.run(
                        [BASH, "-c", '. "$DIR/load_and_validate_env.sh"'],
                        cwd=self.root,
                        env={**self.env, "DIR": str(self.root / "devops/scripts")},
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("config.yaml is invalid", result.stdout)
                    self.assertNotIn(value, result.stdout + result.stderr)
                    self.assertFalse(self.log.exists(), "Config validation must fail before yq exports values")
                    self.assertEqual(self.private.read_text(), "EXISTING='keep me'\n")

    def test_auxiliary_values_match_both_environment_loaders(self):
        output_names = [name for names in AUXILIARY_OUTPUTS.values() for name in names]
        print_values = 'printf "%s\\0" ' + " ".join(f'"${{{name}}}"' for name in output_names)
        for value in ("", ' \tmock"\\$secret; `printf injected`; $(printf injected) == \t '):
            with self.subTest(value=value):
                self.env.update(dict.fromkeys(AUXILIARY_OUTPUTS, value))
                result = self.run_make()
                self.assertEqual(result.returncode, 0, result.stderr)
                for loader in ("load_env.sh", "load_and_validate_env.sh"):
                    with self.subTest(loader=loader):
                        result = subprocess.run(
                            [
                                BASH,
                                "-c",
                                '. "$1" "$2"; ' + print_values,
                                "bash",
                                str(self.root / "devops/scripts" / loader),
                                str(self.private),
                            ],
                            cwd=self.root,
                            env={
                                **self.env,
                                "DIR": str(self.root / "devops/scripts"),
                                "USE_ENV_VARS_NOT_FILES": "true",
                            },
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout.split("\x00"), [value] * len(output_names) + [""])

    def test_incomplete_cache_preserves_existing_files(self):
        invalid_cache = '{"unexpected":{"value":"x"}}'
        self.cache.write_text(invalid_cache)
        self.assert_stopped(self.run_make())
        self.assertEqual(self.cache.read_text(), invalid_cache)
        self.assertNotIn("terraform:output", self.calls)

    def test_multiple_output_documents_are_not_published(self):
        self.env["OUTPUT_JSON"] = VALID_OUTPUT + "\n" + VALID_OUTPUT
        self.assert_stopped(self.run_make())
        self.assertFalse(self.cache.exists())

    def test_successful_output_reaches_ui_with_storage_account(self):
        result = self.run_make()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ui:mockstorage", self.calls)
        self.assertEqual(json.loads(self.cache.read_text()), json.loads(VALID_OUTPUT))
        self.assertIn("STORAGE_ACCOUNT='mockstorage'", self.private.read_text())

    def test_valid_cache_avoids_terraform(self):
        self.cache.write_text(VALID_OUTPUT)
        result = self.run_make()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call.startswith("terraform:") for call in self.calls))
        self.assertIn("ui:mockstorage", self.calls)

    def test_legacy_optional_output_is_preserved_when_present(self):
        output = json.loads(VALID_OUTPUT)
        output["airlock_malware_scan_result_topic_name"] = {"value": "legacy-topic"}
        self.cache.write_text(json.dumps(output))
        result = self.run_make()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AIRLOCK_MALWARE_SCAN_RESULT_TOPIC_NAME='legacy-topic'", self.private.read_text())

    def test_output_values_match_environment_loaders(self):
        output = json.loads(VALID_OUTPUT)
        value = 'mock"\\$storage; echo injected'
        output["static_web_storage"]["value"] = value
        self.env["OUTPUT_JSON"] = json.dumps(output)
        result = self.run_make()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"ui:{value}", self.calls)
        self.assertNotIn("injected", result.stdout)
        # load_and_validate_env.sh sources private.env directly.
        sourced = subprocess.run(
            [BASH, "-c", '. "$1"; printf "%s" "$STORAGE_ACCOUNT"', "bash", str(self.private)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(sourced.returncode, 0, sourced.stderr)
        self.assertEqual(sourced.stdout, value)

    def test_empty_cache_is_regenerated(self):
        self.cache.write_text("")
        result = self.run_make()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("terraform:output", self.calls)
        self.assertIn("ui:mockstorage", self.calls)

    def test_conversion_failure_preserves_environment_and_retries(self):
        output = json.loads(VALID_OUTPUT)
        output["static_web_storage"] = 1
        self.env["OUTPUT_JSON"] = json.dumps(output)
        result = self.run_make()
        self.assert_stopped(result)
        self.assertFalse(self.cache.exists())
        terraform_outputs_before_retry = self.calls.count("terraform:output")

        self.env["OUTPUT_JSON"] = VALID_OUTPUT
        retry = self.run_make()
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertEqual(self.calls.count("terraform:output"), terraform_outputs_before_retry + 1)
        self.assertIn("ui:mockstorage", self.calls)

    def test_converter_reports_invalid_json(self):
        for output in ("", "{}", "[]", "null", '{"partial":', VALID_OUTPUT + "\n" + VALID_OUTPUT):
            with self.subTest(output=output):
                result = subprocess.run(
                    [BASH, "core/terraform/json-to-env.sh"],
                    cwd=self.root,
                    input=output,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertNotEqual(result.returncode, 0)
