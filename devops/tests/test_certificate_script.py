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
    def execute(self, cache_status=0, issuance_status=0):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            log = folder / "calls.jsonl"
            fake = folder / "fake"
            fake.write_text("""#!/usr/bin/env python3
import json,os,pathlib,sys
args=sys.argv[1:]; command=pathlib.Path(sys.argv[0]).name
with open(os.environ['CALL_LOG'],'a') as file: file.write(json.dumps([command,*args])+'\\n')
if command=='python3':
 if 'restore' in args: sys.exit(int(os.environ['CACHE_STATUS']))
elif command=='certbot':
 if os.environ['ISSUANCE_STATUS']!='0': sys.exit(int(os.environ['ISSUANCE_STATUS']))
 d=pathlib.Path(args[args.index('--config-dir')+1])/'live'/args[args.index('--domain')+1];d.mkdir(parents=True)
 for name in ('privkey.pem','fullchain.pem'): (d/name).write_text('test')
elif command=='openssl' and args[0]=='rand': print('private-password')
elif command=='az':
 if args[:3]==['storage','blob','list']: print('[]')
 elif args[:3]==['keyvault','certificate','import']: print(json.dumps({'sid':'https://vault.test/secrets/cert/version'}))
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
                ],
                env=os.environ
                | {
                    "PATH": str(folder) + os.pathsep + os.environ["PATH"],
                    "CALL_LOG": str(log),
                    "CACHE_STATUS": str(cache_status),
                    "ISSUANCE_STATUS": str(issuance_status),
                },
                capture_output=True,
                text=True,
                timeout=15,
            )
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            restore = next(call for call in calls if "restore" in call)
            work = Path(restore[restore.index("--directory") + 1])
            self.assertFalse(work.exists(), "Private temporary files must be removed on every exit")
            self.assertNotIn("private-password", result.stdout + result.stderr)
            return result, calls

    def test_reuse_does_not_call_acme_or_storage(self):
        result, calls = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call[0] == "certbot" or call[1:2] == ["storage"] for call in calls))
        self.assertTrue(any(call[1:4] == ["keyvault", "certificate", "import"] for call in calls))

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
        self.assertEqual(len(calls), 1)

    def test_issuance_failure_does_not_update_cache_or_alias(self):
        result, calls = self.execute(cache_status=3, issuance_status=1)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(any("store" in call or call[1:3] == ["keyvault", "certificate"] for call in calls))


if __name__ == "__main__":
    unittest.main()
