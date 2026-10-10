"""Check OHDSI bootstrap inputs, private access and pipeline cleanup contracts."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "templates/workspace_services/ohdsi"


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.env = os.environ | {
            "PATH": str(self.folder) + os.pathsep + os.environ["PATH"],
            "CALLS": str(self.folder / "calls.jsonl"),
            "OHDSI_ADMIN_PASSWORD": "admin'password",
            "OHDSI_APP_PASSWORD": "app'password",
            "OHDSI_ADMIN_USERNAME": "ohdsi_admin_user",
            "OHDSI_APP_USERNAME": "ohdsi_app_user",
            "OHDSI_ADMIN_ROLE": "ohdsi_admin",
            "OHDSI_APP_ROLE": "ohdsi_app",
            "DATABASE_NAME": "atlas_webapi_db",
            "SCHEMA_NAME": "webapi",
            "MAIN_CONNECTION_STRING": "main",
            "OHDSI_ADMIN_CONNECTION_STRING": "admin",
            "ATLAS_USERS": "admin,secret",
            "WEB_API_URL": "https://webapi.example/WebAPI/",
            "WEB_API_VERSION": "2.12.1",
        }
        self.fake(
            "psql",
            """import json,os,sys
from pathlib import Path
args=sys.argv[1:]
body=Path(args[args.index('-f')+1]).read_text() if '-f' in args else sys.stdin.read()
with open(os.environ['CALLS'],'a') as f:f.write(json.dumps({'args':args,'body':body})+'\\n')
sys.exit(int(os.environ.get('PSQL_EXIT','0')))
""",
        )
        self.fake("envsubst", "import os,sys\nprint(os.path.expandvars(sys.stdin.read()))\n")
        self.fake("md5sum", "import hashlib,sys\nprint(hashlib.md5(sys.stdin.buffer.read()).hexdigest())\n")

    def fake(self, name, body):
        p = self.folder / name
        p.write_text("#!" + sys.executable + "\n" + body)
        p.chmod(0o755)

    def run_script(self, name, **env):
        result = subprocess.run(
            ["bash", str(BUNDLE / "scripts" / name)],
            cwd=BUNDLE / "terraform",
            env=self.env | env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        calls = (
            [json.loads(line) for line in Path(self.env["CALLS"]).read_text().splitlines()]
            if Path(self.env["CALLS"]).exists()
            else []
        )
        return result, calls

    def security_commands(self):
        self.fake(
            "curl",
            """import json,os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['CALLS'],'a') as f:f.write(json.dumps({'curl':args})+'\\n')
if args[0].endswith('/info'):
    sequence=os.environ.get('INFO_VERSIONS','2.12.1').split(',')
    counter=Path(os.environ['CALLS']+'.count')
    count=int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(count+1))
    Path(args[args.index('--output')+1]).write_text(json.dumps({'version':sequence[min(count,len(sequence)-1)]}))
    sys.exit(int(os.environ.get('CURL_EXIT','0')))
if '--output' not in args:print('authentication-token')
""",
        )
        self.fake(
            "jq",
            """import json,sys
from pathlib import Path
args=sys.argv[1:]
expected=args[args.index('--arg')+2]
sys.exit(0 if json.loads(Path(args[-1]).read_text()).get('version')==expected else 1)
""",
        )
        self.fake("sleep", "import time\ntime.sleep(0.01)\n")
        self.fake(
            "timeout",
            """import json,os,signal,subprocess,sys
args=sys.argv[1:]
with open(os.environ['CALLS'],'a') as f:f.write(json.dumps({'timeout':args[:1]})+'\\n')
# Use a shorter test deadline while exercising the real shell loop.
process=subprocess.Popen(args[1:],start_new_session=True)
try:
    sys.exit(process.wait(timeout=2))
except subprocess.TimeoutExpired:
    os.killpg(process.pid,signal.SIGKILL)
    process.wait()
    sys.exit(124)
""",
        )
        self.fake("htpasswd", "print(':test-password-hash')\n")

    def test_security_waits_without_repeated_logins_or_token_output(self):
        self.security_commands()
        result, calls = self.run_script("atlas_security.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        requests = [c["curl"] for c in calls if "curl" in c]
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0][0], "https://webapi.example/WebAPI/info")
        self.assertEqual([c["timeout"] for c in calls if "timeout" in c], [["600"]])
        self.assertIn("--max-time", requests[0])
        self.assertFalse(Path(requests[0][requests[0].index("--output") + 1]).exists())
        self.assertNotIn("--retry", requests[1])
        self.assertEqual(requests[1][requests[1].index("--output") + 1], "/dev/null")
        self.assertNotIn("authentication-token", result.stdout + result.stderr)
        sql = [c for c in calls if "args" in c]
        self.assertTrue(all("-e" not in c["args"] for c in sql))
        self.assertIn(":'password_hash'", sql[2]["body"])
        self.assertIn("NOT EXISTS", sql[3]["body"])
        self.assertIn(r"\if :role_assigned", sql[3]["body"])
        self.assertIn("RAISE EXCEPTION", sql[3]["body"])

    def test_readiness_failure_prevents_database_changes_and_login(self):
        self.security_commands()
        result, calls = self.run_script("atlas_security.sh", CURL_EXIT="22")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.returncode, 124)
        self.assertTrue(all("args" not in c for c in calls))
        self.assertTrue(all(c["curl"][0].endswith("/info") for c in calls if "curl" in c))

    def test_unexpected_version_prevents_database_changes_and_login(self):
        self.security_commands()
        result, calls = self.run_script("atlas_security.sh", INFO_VERSIONS="2.11.0")
        self.assertEqual(result.returncode, 124)
        self.assertTrue(all("args" not in c for c in calls))
        self.assertTrue(all(c["curl"][0].endswith("/info") for c in calls if "curl" in c))

    def test_stale_http_success_is_retried_before_security_initialisation(self):
        self.security_commands()
        result, calls = self.run_script("atlas_security.sh", INFO_VERSIONS="2.11.0,2.12.1")
        self.assertEqual(result.returncode, 0, result.stderr)
        requests = [c["curl"] for c in calls if "curl" in c]
        self.assertEqual([r[0].rsplit("/", 1)[1] for r in requests], ["info", "info", "db"])
        first_sql = next(i for i, c in enumerate(calls) if "args" in c)
        self.assertEqual(sum("curl" in c for c in calls[:first_sql]), 2)
        self.assertNotIn("--retry", requests[-1])

    def test_passwords_use_psql_quoted_variables_without_sql_echo(self):
        result, calls = self.run_script("atlas_db_init.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertIn("admin_password=admin'password", calls[0]["args"])
        self.assertIn("app_password=app'password", calls[0]["args"])
        self.assertIn(":'admin_password'", calls[0]["body"])
        self.assertIn(":'app_password'", calls[0]["body"])
        for call in calls:
            self.assertIn("ON_ERROR_STOP=1", call["args"])
            self.assertNotIn("-e", call["args"])
        self.assertNotIn("password", result.stdout + result.stderr)

    def test_role_creation_failure_stops_before_schema_creation(self):
        result, calls = self.run_script("atlas_db_init.sh", PSQL_EXIT="7")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)

    def test_roles_and_schema_are_safe_to_repeat(self):
        roles = (BUNDLE / "sql/atlas_create_roles_users.sql").read_text()
        self.assertEqual(roles.count("WHERE NOT EXISTS"), 4)
        self.assertEqual(roles.count("\\gexec"), 4)
        self.assertIn("CREATE SCHEMA IF NOT EXISTS", (BUNDLE / "sql/atlas_create_schema.sql").read_text())


class BundleContractTests(unittest.TestCase):
    def test_database_and_apps_disable_public_access(self):
        for filename in ("atlas_database.tf", "atlas_ui.tf", "ohdsi_web_api.tf"):
            with self.subTest(filename=filename):
                source = (BUNDLE / "terraform" / filename).read_text()
                self.assertRegex(source, r"public_network_access_enabled\s*=\s*false")

    def test_uninstall_removes_only_owned_firewall_collections(self):
        schema = json.loads((BUNDLE / "template_schema.json").read_text())
        uninstall = schema["pipeline"]["uninstall"]
        cleanup = [s for s in uninstall if s.get("resourceTemplateName") == "tre-shared-service-firewall"]
        self.assertEqual(len(cleanup), 1)
        self.assertEqual(cleanup[0]["resourceAction"], "upgrade")
        self.assertEqual(
            {p["name"]: p["value"] for p in cleanup[0]["properties"]},
            {
                "network_rule_collections": {"name": "nrc_svc_{{ resource.id }}"},
                "rule_collections": {"name": "arc_svc_{{ resource.id }}"},
            },
        )
        for prop in cleanup[0]["properties"]:
            self.assertEqual(prop["arraySubstitutionAction"], "remove")
            self.assertEqual(prop["arrayMatchField"], "name")
        self.assertLess(uninstall.index(cleanup[0]), next(i for i, s in enumerate(uninstall) if s["stepId"] == "main"))

    def test_bootstrap_version_matches_pinned_image(self):
        source = (BUNDLE / "terraform/atlas_security.tf").read_text()
        self.assertRegex(source, r"WEB_API_VERSION\s*=\s*local.ohdsi_api_docker_image_tag")
        manifest = yaml.safe_load((BUNDLE / "porter.yaml").read_text())
        self.assertEqual(manifest["version"], "0.3.14")
