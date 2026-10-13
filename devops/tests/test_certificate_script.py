"""Check issuance, cache failure and secret handling at the shell boundary."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "templates/shared_services/certs/scripts/letsencrypt.sh"


class CertificateScriptTests(unittest.TestCase):
    def execute(
        self,
        cache_status=0,
        issuance_status=0,
        *,
        cache_vault="cache-vault",
        start=False,
        start_status=0,
        stop_status=0,
        store_status=0,
        alias_status=0,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            private_temp = folder / "private-temp"
            private_temp.mkdir()
            log = folder / "calls.jsonl"
            fake = folder / "fake"
            fake.write_text("""#!/usr/bin/env python3
import json,os,pathlib,sys
args=sys.argv[1:]; command=pathlib.Path(sys.argv[0]).name
with open(os.environ['CALL_LOG'],'a') as file: file.write(json.dumps([command,*args])+'\\n')
if command=='python3':
 if 'restore' in args: sys.exit(int(os.environ['CACHE_STATUS']))
 if 'store' in args: sys.exit(int(os.environ['STORE_STATUS']))
elif command=='certbot':
 if os.environ['ISSUANCE_STATUS']!='0': sys.exit(int(os.environ['ISSUANCE_STATUS']))
 d=pathlib.Path(args[args.index('--config-dir')+1])/'live'/args[args.index('--domain')+1];d.mkdir(parents=True)
 for name in ('privkey.pem','fullchain.pem'): (d/name).write_text('test')
elif command=='openssl' and args[0]=='rand': print('private-password')
elif command=='az':
 if args[:3]==['storage','blob','list']: print('[]')
 elif args[:3]==['network','application-gateway','start']: sys.exit(int(os.environ['START_STATUS']))
 elif args[:3]==['network','application-gateway','stop']: sys.exit(int(os.environ['STOP_STATUS']))
 elif args[:3]==['keyvault','certificate','import']:
  if os.environ['ALIAS_STATUS']!='0': sys.exit(int(os.environ['ALIAS_STATUS']))
  print(json.dumps({'sid':'https://vault.test/secrets/cert/version'}))
 elif args[:3]==['keyvault','secret','set']:
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
                    *(["--cache_vault_name", cache_vault] if cache_vault is not None else []),
                    *(["--start_gateway", "true"] if start else []),
                ],
                env=os.environ
                | {
                    "PATH": str(folder) + os.pathsep + os.environ["PATH"],
                    "CALL_LOG": str(log),
                    "CACHE_STATUS": str(cache_status),
                    "ISSUANCE_STATUS": str(issuance_status),
                    "START_STATUS": str(start_status),
                    "STOP_STATUS": str(stop_status),
                    "STORE_STATUS": str(store_status),
                    "ALIAS_STATUS": str(alias_status),
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

    def test_reuse_does_not_call_acme_or_storage(self):
        result, calls = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call[0] == "certbot" or call[1:2] == ["storage"] for call in calls))
        self.assertTrue(any(call[1:4] == ["keyvault", "certificate", "import"] for call in calls))

    def test_default_deployment_does_not_read_or_write_a_cache(self):
        for cache_vault in (None, ""):
            with self.subTest(cache_vault=cache_vault):
                result, calls = self.execute(cache_vault=cache_vault)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(any("restore" in call or "store" in call for call in calls))
                self.assertEqual(sum(call[0] == "certbot" for call in calls), 1)

    def test_retained_material_uses_a_separate_vault_from_the_active_alias(self):
        result, calls = self.execute(cache_status=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        retained = [call for call in calls if "restore" in call or "store" in call]
        self.assertEqual(len(retained), 2)
        for call in retained:
            self.assertEqual(call[call.index("--vault") + 1], "cache-vault")
        active = [call for call in calls if call[1:2] == ["keyvault"]]
        self.assertEqual(len(active), 2)
        for call in active:
            self.assertEqual(call[call.index("--vault-name") + 1], "vault")

    def test_core_vault_cannot_be_used_for_retention(self):
        for cache_vault in ("vault", "VAULT"):
            with self.subTest(cache_vault=cache_vault):
                result, calls = self.execute(cache_vault=cache_vault)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any("restore" in call or "store" in call or call[0] == "certbot" for call in calls))
                self.assertEqual(calls[-1][1:4], ["network", "application-gateway", "stop"])

    def test_missing_cache_issues_once_and_persists_before_alias_update(self):
        result, calls = self.execute(cache_status=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(call[0] == "certbot" for call in calls), 1)
        store = next(i for i, call in enumerate(calls) if "store" in call)
        alias = next(i for i, call in enumerate(calls) if call[1:4] == ["keyvault", "certificate", "import"])
        self.assertLess(store, alias)

    def test_cache_failure_stops_before_acme_and_alias_changes(self):
        result, calls = self.execute(cache_status=1)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(any(call[0] == "certbot" or call[1:2] == ["keyvault"] for call in calls))

    def test_issuance_failure_does_not_update_cache_or_alias(self):
        result, calls = self.execute(cache_status=3, issuance_status=1)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(any("store" in call or call[1:3] == ["keyvault", "certificate"] for call in calls))

    def test_success_stops_gateway_after_updating_certificate(self):
        result, calls = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1][1:4], ["network", "application-gateway", "stop"])
        self.assertEqual(sum(call[1:4] == ["network", "application-gateway", "stop"] for call in calls), 1)

    def test_certificate_failures_still_stop_gateway(self):
        for settings in (
            {"cache_status": 23},
            {"cache_status": 3, "issuance_status": 24},
            {"cache_status": 3, "store_status": 25},
            {"alias_status": 26},
        ):
            with self.subTest(settings=settings):
                result, calls = self.execute(**settings)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls[-1][1:4], ["network", "application-gateway", "stop"])

    def test_renew_starts_gateway_inside_cleanup_scope(self):
        result, calls = self.execute(start=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[0][1:4], ["network", "application-gateway", "start"])
        self.assertEqual(calls[-1][1:4], ["network", "application-gateway", "stop"])

    def test_failed_start_still_attempts_stop(self):
        result, calls = self.execute(start=True, start_status=27)
        self.assertEqual(result.returncode, 27)
        self.assertEqual(calls[-1][1:4], ["network", "application-gateway", "stop"])
        self.assertFalse(any("restore" in call or call[0] == "certbot" for call in calls))

    def test_cleanup_failure_does_not_mask_original_error(self):
        result, calls = self.execute(cache_status=23, stop_status=28)
        self.assertEqual(result.returncode, 23)
        self.assertIn("Failed to stop the certificate application gateway", result.stderr)

    def test_cleanup_failure_fails_an_otherwise_successful_operation(self):
        result, calls = self.execute(stop_status=28)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Failed to stop the certificate application gateway", result.stderr)


if __name__ == "__main__":
    unittest.main()
