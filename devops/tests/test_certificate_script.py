"""Check issuance, reuse failure and secret handling at the shell boundary."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "templates/shared_services/certs/scripts/letsencrypt.sh"
CURRENT_SECRET_ID = "https://vault.vault.azure.net/secrets/nexus-e2e-random/" + "a" * 32
IMPORTED_SECRET_ID = "https://vault.vault.azure.net/secrets/nexus-e2e-random/" + "b" * 32


class CertificateScriptTests(unittest.TestCase):
    def execute(
        self,
        reuse_status=0,
        issuance_status=0,
        *,
        reuse_current=True,
        reuse_metadata=None,
        start=None,
        start_status=0,
        stop_status=0,
        validation_status=0,
        alias_status=0,
        password_status=0,
        gateway_status=0,
        gateway_state=None,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            if gateway_state is None:
                gateway_state = folder / "gateway-state"
                gateway_state.write_text("Running")
            private_temp = folder / "private-temp"
            private_temp.mkdir()
            log = folder / "calls.jsonl"
            fake = folder / "fake"
            fake.write_text("""#!/usr/bin/env python3
import json,os,pathlib,sys
args=sys.argv[1:]; command=pathlib.Path(sys.argv[0]).name
gateway_state=pathlib.Path(os.environ['GATEWAY_STATE'])
with open(os.environ['CALL_LOG'],'a') as file: file.write(json.dumps([command,*args])+'\\n')
if command=='python3':
 if 'restore' in args:
  if os.environ['REUSE_STATUS']=='0' and os.environ['REUSE_METADATA']:
   d=pathlib.Path(args[args.index('--directory')+1])
   (d/'reuse.json').write_text(os.environ['REUSE_METADATA'])
  sys.exit(int(os.environ['REUSE_STATUS']))
 if 'validate' in args: sys.exit(int(os.environ['VALIDATION_STATUS']))
elif command=='certbot':
 if gateway_state.read_text()!='Running': sys.exit(33)
 if os.environ['ISSUANCE_STATUS']!='0': sys.exit(int(os.environ['ISSUANCE_STATUS']))
 d=pathlib.Path(args[args.index('--config-dir')+1])/'live'/args[args.index('--domain')+1];d.mkdir(parents=True)
 for name in ('privkey.pem','fullchain.pem'): (d/name).write_text('test')
elif command=='openssl' and args[0]=='rand': print('private-password')
elif command=='az':
 if args[:3]==['storage','blob','list']: print('[]')
 elif args[:3]==['network','application-gateway','start']:
  if os.environ['START_STATUS']!='0': sys.exit(int(os.environ['START_STATUS']))
  gateway_state.write_text('Running')
 elif args[:3]==['network','application-gateway','stop']:
  if os.environ['STOP_STATUS']!='0': sys.exit(int(os.environ['STOP_STATUS']))
  gateway_state.write_text('Stopped')
 elif args[:3]==['keyvault','certificate','import']:
  if os.environ['ALIAS_STATUS']!='0': sys.exit(int(os.environ['ALIAS_STATUS']))
  print(json.dumps({'sid':os.environ['IMPORTED_SECRET_ID']}))
 elif args[:4]==['network','application-gateway','ssl-cert','update']: sys.exit(int(os.environ['GATEWAY_STATUS']))
 elif args[:3]==['keyvault','secret','set']:
  if os.environ['PASSWORD_STATUS']!='0': sys.exit(int(os.environ['PASSWORD_STATUS']))
  assert '--output' in args and args[args.index('--output')+1]=='none'
  assert pathlib.Path(args[args.index('--file')+1]).read_text()=='private-password'
""")
            fake.chmod(0o700)
            for name in ("python3", "certbot", "az", "openssl", "sleep"):
                (folder / name).symlink_to(fake)
            # The fake uses the host interpreter, not the intercepted python3 name.
            fake.write_text(fake.read_text().replace("#!/usr/bin/env python3", "#!" + os.sys.executable))
            script = folder / "letsencrypt.sh"
            script.write_text(SCRIPT.read_text().replace("/opt/certbot/bin/certbot", str(folder / "certbot")))
            result = subprocess.run(
                [
                    "bash",
                    str(script),
                    "--storage_account_name",
                    "storage",
                    "--fqdn",
                    "nexus.example.test",
                    "--keyvault_name",
                    "vault",
                    "--resource_group_name",
                    "rg",
                    "--application_gateway_name",
                    "agw",
                    "--cert_name",
                    "nexus-e2e-random",
                    "--password_name",
                    "password",
                    *(["--start_gateway", str(start).lower()] if start is not None else []),
                ],
                env=os.environ
                | {
                    "PATH": str(folder) + os.pathsep + os.environ["PATH"],
                    "CALL_LOG": str(log),
                    "REUSE_STATUS": str(reuse_status),
                    "REUSE_METADATA": (
                        json.dumps({"is_current": reuse_current, "secret_id": CURRENT_SECRET_ID})
                        if reuse_metadata is None
                        else reuse_metadata
                    ),
                    "IMPORTED_SECRET_ID": IMPORTED_SECRET_ID,
                    "ISSUANCE_STATUS": str(issuance_status),
                    "START_STATUS": str(start_status),
                    "STOP_STATUS": str(stop_status),
                    "VALIDATION_STATUS": str(validation_status),
                    "ALIAS_STATUS": str(alias_status),
                    "PASSWORD_STATUS": str(password_status),
                    "GATEWAY_STATUS": str(gateway_status),
                    "GATEWAY_STATE": str(gateway_state),
                    "TMPDIR": str(private_temp),
                },
                capture_output=True,
                text=True,
                timeout=15,
            )
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(list(private_temp.iterdir()), [], "Private temporary files must be removed on every exit")
            self.assertNotIn("private-password", result.stdout + result.stderr)
            return result, calls

    def test_default_install_reuses_the_core_vault_without_acme_or_storage(self):
        result, calls = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call[0] == "certbot" or call[1:2] == ["storage"] for call in calls))
        restore = next(call for call in calls if "restore" in call)
        self.assertEqual(restore[restore.index("--vault") + 1], "vault")
        self.assertEqual(restore[restore.index("--cert-name") + 1], "nexus-e2e-random")
        self.assertFalse(any(call[0] == "openssl" or call[1:2] == ["keyvault"] for call in calls))
        gateway = next(call for call in calls if call[1:4] == ["network", "application-gateway", "ssl-cert"])
        self.assertEqual(gateway[gateway.index("--key-vault-secret-id") + 1], CURRENT_SECRET_ID)

    def test_recovered_older_certificate_is_imported_without_acme(self):
        result, calls = self.execute(reuse_current=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call[0] == "certbot" for call in calls))
        self.assertEqual(sum(call[1:4] == ["keyvault", "certificate", "import"] for call in calls), 1)
        self.assertEqual(sum(call[1:4] == ["keyvault", "secret", "set"] for call in calls), 1)
        gateway = next(call for call in calls if call[1:4] == ["network", "application-gateway", "ssl-cert"])
        self.assertEqual(gateway[gateway.index("--key-vault-secret-id") + 1], IMPORTED_SECRET_ID)

    def test_missing_or_invalid_reuse_metadata_stops_before_writes(self):
        for metadata in ("", "{}", '{"is_current":"true"}', '{"is_current":true,"secret_id":null}'):
            with self.subTest(metadata=metadata):
                result, calls = self.execute(reuse_metadata=metadata)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any(call[0] in ("openssl", "certbot") or call[1:2] == ["keyvault"] for call in calls))
                self.assertFalse(any(call[1:4] == ["network", "application-gateway", "ssl-cert"] for call in calls))
                self.assertEqual(calls[-1][1:4], ["network", "application-gateway", "stop"])

    def test_bootstrap_or_due_certificate_issues_once_and_validates_before_import(self):
        result, calls = self.execute(reuse_status=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(call[0] == "certbot" for call in calls), 1)
        validate = next(i for i, call in enumerate(calls) if "validate" in call)
        certificate = next(i for i, call in enumerate(calls) if call[1:4] == ["keyvault", "certificate", "import"])
        password = next(i for i, call in enumerate(calls) if call[1:4] == ["keyvault", "secret", "set"])
        self.assertLess(validate, certificate)
        self.assertLess(certificate, password)
        self.assertFalse(any("store" in call for call in calls))

    def test_lookup_failure_stops_before_issuance_or_vault_changes(self):
        result, calls = self.execute(reuse_status=23)
        self.assertEqual(result.returncode, 23)
        self.assertFalse(any(call[0] == "certbot" or call[1:2] == ["keyvault"] for call in calls))

    def test_invalid_new_material_is_not_imported(self):
        result, calls = self.execute(reuse_status=3, validation_status=24)
        self.assertEqual(result.returncode, 24)
        self.assertFalse(any(call[1:2] == ["keyvault"] for call in calls))

    def test_issuance_failure_does_not_update_certificate_or_password(self):
        result, calls = self.execute(reuse_status=3, issuance_status=25)
        self.assertEqual(result.returncode, 25)
        self.assertFalse(any(call[1:2] == ["keyvault"] for call in calls))

    def test_install_retry_restarts_the_gateway_stopped_by_the_failed_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            gateway_state = Path(temporary) / "gateway-state"
            gateway_state.write_text("Running")
            failed, _ = self.execute(reuse_status=3, issuance_status=25, gateway_state=gateway_state)
            self.assertEqual(failed.returncode, 25)
            self.assertEqual(gateway_state.read_text(), "Stopped")

            retried, calls = self.execute(reuse_status=3, gateway_state=gateway_state)
            self.assertEqual(retried.returncode, 0, retried.stderr)
            start = next(i for i, call in enumerate(calls) if call[1:4] == ["network", "application-gateway", "start"])
            issuance = next(i for i, call in enumerate(calls) if call[0] == "certbot")
            self.assertLess(start, issuance)
            self.assertEqual(gateway_state.read_text(), "Stopped")

    def test_install_start_failure_stops_before_issuance(self):
        result, calls = self.execute(reuse_status=3, start_status=29)
        self.assertEqual(result.returncode, 29)
        self.assertFalse(any(call[0] == "certbot" for call in calls))
        self.assertEqual(calls[-1][1:4], ["network", "application-gateway", "stop"])

    def test_retry_after_password_or_gateway_failure_uses_the_imported_certificate_without_vault_writes(self):
        for failure in ({"password_status": 26}, {"gateway_status": 26}):
            with self.subTest(failure=failure):
                failed, initial = self.execute(reuse_status=3, **failure)
                self.assertEqual(failed.returncode, 26)
                self.assertTrue(any(call[1:4] == ["keyvault", "certificate", "import"] for call in initial))
                retried, calls = self.execute(reuse_status=0)
                self.assertEqual(retried.returncode, 0, retried.stderr)
                self.assertFalse(any(call[0] in ("openssl", "certbot") or call[1:2] == ["keyvault"] for call in calls))
                gateway = next(call for call in calls if call[1:4] == ["network", "application-gateway", "ssl-cert"])
                self.assertEqual(gateway[gateway.index("--key-vault-secret-id") + 1], CURRENT_SECRET_ID)

    def test_success_stops_gateway_after_updating_certificate(self):
        result, calls = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1][1:4], ["network", "application-gateway", "stop"])
        self.assertEqual(sum(call[1:4] == ["network", "application-gateway", "stop"] for call in calls), 1)

    def test_failures_still_stop_gateway_and_remove_private_files(self):
        for settings in (
            {"reuse_status": 23},
            {"reuse_status": 3, "issuance_status": 24},
            {"reuse_status": 3, "validation_status": 25},
            {"reuse_current": False, "alias_status": 26},
            {"reuse_current": False, "password_status": 27},
            {"gateway_status": 28},
            {"start": True, "start_status": 29},
        ):
            with self.subTest(settings=settings):
                result, calls = self.execute(**settings)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls[-1][1:4], ["network", "application-gateway", "stop"])

    def test_renew_reuses_certificate_inside_gateway_cleanup_scope(self):
        result, calls = self.execute(start=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call[0] == "certbot" for call in calls))
        self.assertFalse(any(call[0] == "openssl" or call[1:2] == ["keyvault"] for call in calls))
        self.assertEqual(calls[0][1:4], ["network", "application-gateway", "start"])
        self.assertEqual(calls[-1][1:4], ["network", "application-gateway", "stop"])

    def test_stop_failure_fails_an_otherwise_successful_operation(self):
        result, _ = self.execute(stop_status=31)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Failed to stop", result.stderr)

    def test_cleanup_preserves_the_original_error(self):
        result, _ = self.execute(reuse_status=23, stop_status=31)
        self.assertEqual(result.returncode, 23)
        self.assertIn("Failed to stop", result.stderr)


if __name__ == "__main__":
    unittest.main()
