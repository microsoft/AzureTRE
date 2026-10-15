"""Check certificate reuse using a local CA and mocked vault access."""

import base64
from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
import re
from datetime import datetime, timedelta, timezone
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HELPER = Path(__file__).resolve().parents[2] / "templates/shared_services/certs/scripts/certificate_reuse.py"
SPEC = importlib.util.spec_from_file_location("certificate_reuse", HELPER)
REUSE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REUSE)
FQDN = "nexus-tre.example.test"


class CertificateReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.command(
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "365",
            "-subj",
            "/CN=Test Root",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-keyout",
            str(cls.root / "ca.key"),
            "-out",
            str(cls.root / "ca.pem"),
        )
        for name, dns in (("valid", FQDN), ("wrong", "other.example.test"), ("wildcard", "*.example.test")):
            folder = cls.root / name
            folder.mkdir()
            cls.command(
                "req",
                "-new",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-subj",
                "/CN=" + dns,
                "-keyout",
                str(folder / "privkey.pem"),
                "-out",
                str(folder / "request.pem"),
            )
            (folder / "extensions").write_text(
                "basicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\n"
                "extendedKeyUsage=serverAuth\nsubjectAltName=DNS:" + dns + "\n"
            )
            cls.command(
                "x509",
                "-req",
                "-in",
                str(folder / "request.pem"),
                "-CA",
                str(cls.root / "ca.pem"),
                "-CAkey",
                str(cls.root / "ca.key"),
                "-CAcreateserial",
                "-days",
                "90",
                "-extfile",
                str(folder / "extensions"),
                "-out",
                str(folder / "fullchain.pem"),
            )
            (folder / "fullchain.pem").write_text(
                (folder / "fullchain.pem").read_text() + (cls.root / "ca.pem").read_text()
            )
        cls.command(
            "pkcs12",
            "-export",
            "-inkey",
            str(cls.root / "valid/privkey.pem"),
            "-in",
            str(cls.root / "valid/fullchain.pem"),
            "-out",
            str(cls.root / "valid.pfx"),
            "-passout",
            "pass:",
        )

        cls.publics = {}
        for kind in ("valid", "wrong"):
            target = cls.root / (kind + ".der")
            cls.command("x509", "-in", str(cls.root / kind / "fullchain.pem"), "-outform", "DER", "-out", str(target))
            cls.publics[kind] = target.read_bytes()
        terraform = HELPER.parents[1] / "terraform/certificate.tf"
        encoded = re.search(r'contents\s*=\s*"([^"]+)"', terraform.read_text())[1]
        (cls.root / "bootstrap.pfx").write_bytes(base64.b64decode(encoded))
        cls.command(
            "pkcs12",
            "-in",
            str(cls.root / "bootstrap.pfx"),
            "-passin",
            "pass:0000000000",
            "-nokeys",
            "-out",
            str(cls.root / "bootstrap.pem"),
        )
        cls.command(
            "x509", "-in", str(cls.root / "bootstrap.pem"), "-outform", "DER", "-out", str(cls.root / "bootstrap.der")
        )
        cls.publics["bootstrap"] = (cls.root / "bootstrap.der").read_bytes()

    @staticmethod
    def command(*args):
        subprocess.run(["openssl", *args], capture_output=True, check=True, timeout=20)

    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for name in ("privkey.pem", "fullchain.pem"):
            shutil.copyfile(self.root / "valid" / name, self.folder / name)
        self.enterContext(patch.dict(os.environ, {"SSL_CERT_FILE": str(self.root / "ca.pem")}))
        self.certificates = {}
        self.secrets = {}
        self.public = {}
        self.calls = []
        self.latest = self.add_certificate("a" * 32, 100)
        self.current = None
        self.history = None
        self.original_run = REUSE.run
        self.enterContext(patch.object(REUSE, "azure", side_effect=self.azure))
        self.enterContext(patch.object(REUSE, "run", side_effect=self.command_or_download))

    def add_certificate(self, version, created, kind="valid", enabled=True, content_type="application/x-pkcs12"):
        base = "https://vault.vault.azure.net/"
        cert = {
            "id": base + "certificates/nexus-ssl/" + version,
            "sid": base + "secrets/nexus-ssl/" + version,
            "attributes": {"enabled": enabled, "created": created},
            "policy": {"secretProperties": {"contentType": "application/x-pkcs12"}},
        }
        self.certificates[cert["id"]] = cert
        self.public[cert["id"]] = self.publics[kind]
        if content_type == "application/x-pem-file":
            value = (self.root / "valid/privkey.pem").read_text() + (self.root / "valid/fullchain.pem").read_text()
        else:
            value = base64.b64encode((self.root / "valid.pfx").read_bytes()).decode()
        self.secrets[cert["sid"]] = {
            "id": cert["sid"],
            "attributes": {"enabled": enabled},
            "contentType": content_type,
            "value": value,
        }
        return cert

    def azure(self, *args):
        self.calls.append(args)
        if args == ("cloud", "show"):
            return {"suffixes": {"keyvaultDns": ".vault.azure.net"}}
        if args[:3] == ("keyvault", "certificate", "list-versions"):
            return copy.deepcopy(self.history if self.history is not None else list(self.certificates.values()))
        if args[:3] == ("keyvault", "certificate", "show"):
            if "--id" in args:
                return copy.deepcopy(self.certificates[args[args.index("--id") + 1]])
            if self.current is not None and sum("--vault-name" in c and c[:3] == args[:3] for c in self.calls) > 1:
                return copy.deepcopy(self.current)
            return copy.deepcopy(self.latest)
        if args[:3] == ("keyvault", "secret", "show"):
            return copy.deepcopy(self.secrets[args[args.index("--id") + 1]])
        self.fail(f"Unexpected Azure command {args[:3]}")

    def command_or_download(self, arguments):
        if arguments[:4] == ["az", "keyvault", "certificate", "download"]:
            self.calls.append(tuple(arguments))
            Path(arguments[arguments.index("--file") + 1]).write_bytes(
                self.public[arguments[arguments.index("--id") + 1]]
            )
            return ""
        return self.original_run(arguments)

    def restore(self):
        return REUSE.restore("vault", "nexus-ssl", FQDN, self.folder)

    def test_bootstrap_fingerprint_matches_the_checked_in_terraform_certificate(self):
        self.assertEqual(hashlib.sha256(self.publics["bootstrap"]).hexdigest(), REUSE.BOOTSTRAP_SHA256)

    def test_existing_certificate_is_reused_without_listing_older_versions(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertTrue(self.restore())
        self.assertIn("no ACME request required", output.getvalue())
        self.assertNotIn("PRIVATE KEY", output.getvalue())
        self.assertFalse(any("list-versions" in call for call in self.calls))
        self.assertIn(("keyvault", "secret", "show", "--id", self.latest["sid"]), self.calls)
        self.assertEqual(
            json.loads((self.folder / "reuse.json").read_text()),
            {"is_current": True, "secret_id": self.latest["sid"]},
        )

    def test_first_install_with_only_the_bootstrap_requires_issuance(self):
        self.certificates.clear()
        self.latest = self.add_certificate("b" * 32, 200, "bootstrap")
        self.assertFalse(self.restore())
        self.assertFalse(any(call[:3] == ("keyvault", "secret", "show") for call in self.calls))

    def test_reinstall_reuses_issued_material_behind_multiple_bootstrap_versions(self):
        issued = self.latest
        self.add_certificate("b" * 32, 200, "bootstrap")
        self.latest = self.add_certificate("c" * 32, 300, "bootstrap")
        self.assertTrue(self.restore())
        self.assertEqual((self.folder / "selected.der").read_bytes(), self.publics["valid"])
        self.assertEqual(
            json.loads((self.folder / "reuse.json").read_text()),
            {"is_current": False, "secret_id": issued["sid"]},
        )

    def test_selection_handles_more_than_one_service_page_and_unsorted_versions(self):
        for index in range(1, 28):
            self.latest = self.add_certificate(f"{index:032x}", 200 + index, "bootstrap")
        self.history = list(reversed(list(self.certificates.values())))
        self.assertTrue(self.restore())
        self.assertTrue(any("list-versions" in call for call in self.calls))

    def test_newest_issued_version_is_not_skipped_when_disabled_or_wrong(self):
        for kind, enabled in (("valid", False), ("wrong", True)):
            with self.subTest(kind=kind, enabled=enabled):
                self.add_certificate("d" * 32, 200, kind, enabled)
                self.latest = self.add_certificate("e" * 32, 300, "bootstrap")
                self.calls.clear()
                with self.assertRaises((ValueError, REUSE.CertificateReuseError)):
                    self.restore()
                older = "https://vault.vault.azure.net/certificates/nexus-ssl/" + "a" * 32
                self.assertFalse(any("--id" in call and older in call for call in self.calls))

    def test_equal_creation_times_for_different_issued_versions_are_rejected(self):
        self.add_certificate("d" * 32, 100)
        self.latest = self.add_certificate("e" * 32, 300, "bootstrap")
        with self.assertRaisesRegex(REUSE.CertificateReuseError, "newest"):
            self.restore()

    def test_iso_creation_dates_are_supported(self):
        self.latest["attributes"]["created"] = "2026-10-13T12:00:00+00:00"
        self.latest = self.add_certificate("b" * 32, "2026-10-14T12:00:00Z", "bootstrap")
        self.assertTrue(self.restore())

    def test_incomplete_or_duplicate_history_is_rejected(self):
        previous = self.latest
        self.latest = self.add_certificate("b" * 32, 200, "bootstrap")
        for history in ([], [previous], [self.latest, self.latest]):
            self.history = history
            with self.subTest(history=history), self.assertRaises(REUSE.CertificateReuseError):
                self.restore()

    def test_secret_format_is_read_from_the_exact_version_not_the_current_policy(self):
        self.latest = self.add_certificate("a" * 32, 100, content_type="application/x-pem-file")
        self.assertTrue(self.restore())
        self.assertTrue(REUSE.validate_material(self.folder, FQDN))
        self.assertNotIn("PRIVATE KEY", (self.folder / "fullchain.pem").read_text())

    def test_wrong_vault_name_or_version_is_rejected_before_secret_access(self):
        sid = self.latest["sid"]
        for value in (
            sid.replace("vault.vault.azure.net", "other.vault.azure.net"),
            sid.replace("nexus-ssl", "another-service"),
            sid.replace("a" * 32, "b" * 32),
            sid + "?leak=value",
            sid.replace("https:", "http:"),
        ):
            self.latest["sid"] = value
            self.calls.clear()
            with self.subTest(value=value), self.assertRaises(REUSE.CertificateReuseError):
                self.restore()
            self.assertFalse(any(call[:3] == ("keyvault", "secret", "show") for call in self.calls))
        self.latest["sid"] = sid

    def test_disabled_or_malformed_secret_is_rejected(self):
        original = copy.deepcopy(self.secrets[self.latest["sid"]])
        for changes in (
            {"attributes": {"enabled": False}},
            {"contentType": "text/plain"},
            {"value": "not a PFX"},
            {"id": "https://unrelated.example/secrets/foo"},
        ):
            self.secrets[self.latest["sid"]] = original | changes
            with self.subTest(changes=changes), self.assertRaises((ValueError, REUSE.CertificateReuseError)):
                self.restore()

    def test_lookup_failure_never_means_issuance_is_required(self):
        for detail in ("CertificateNotFound", "Forbidden", "connection reset"):
            with patch.object(REUSE, "azure", side_effect=REUSE.CertificateReuseError(detail)):
                with self.assertRaises(REUSE.CertificateReuseError):
                    self.restore()
        self.assertIsNone(REUSE.DEADLINE.get())

    def test_change_during_lookup_is_rejected(self):
        self.current = self.add_certificate("b" * 32, 200)
        with self.assertRaisesRegex(REUSE.CertificateReuseError, "changed during lookup"):
            self.restore()

    def test_disabled_active_certificate_is_rejected(self):
        self.latest["attributes"]["enabled"] = False
        with self.assertRaisesRegex(REUSE.CertificateReuseError, "disabled"):
            self.restore()

    def test_expiry_boundary_and_expired_certificate_request_renewal(self):
        dates = self.original_run(["openssl", "x509", "-in", str(self.folder / "fullchain.pem"), "-noout", "-enddate"])
        expiry = datetime.strptime(dates.strip().split("=", 1)[1], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        self.assertTrue(REUSE.validate_material(self.folder, FQDN, expiry - timedelta(days=30, seconds=1)))
        self.assertFalse(REUSE.validate_material(self.folder, FQDN, expiry - timedelta(days=30)))
        self.assertFalse(REUSE.validate_material(self.folder, FQDN, expiry + timedelta(seconds=1)))
        with patch.object(REUSE, "validate_material", return_value=False):
            self.assertFalse(self.restore())

    def test_mismatched_certificate_secret_does_not_reuse_material(self):
        self.public[self.latest["id"]] = self.publics["wrong"]
        with self.assertRaisesRegex(REUSE.CertificateReuseError, "does not match"):
            self.restore()

    def test_all_cli_operations_are_read_only(self):
        self.latest = self.add_certificate("b" * 32, 200, "bootstrap")
        self.assertTrue(self.restore())
        for call in self.calls:
            self.assertFalse(set(call) & {"recover", "delete", "purge", "import", "set"})

    def test_command_failure_never_discloses_output_or_secret_arguments(self):
        for failure in (
            subprocess.CalledProcessError(1, ["az", "secret-password"], output="private-key", stderr="private-key"),
            subprocess.TimeoutExpired(["az", "secret-password"], 180, output="private-key"),
        ):
            with patch.object(REUSE.subprocess, "run", side_effect=failure):
                with self.assertRaises(REUSE.CertificateReuseError) as caught:
                    self.original_run(["az", "secret-password"])
            self.assertNotIn("secret-password", str(caught.exception))
            self.assertNotIn("private-key", str(caught.exception))

    def test_lookup_deadline_bounds_the_next_command(self):
        token = REUSE.DEADLINE.set(REUSE.time.monotonic() - 1)
        try:
            with patch.object(REUSE.subprocess, "run") as command:
                with self.assertRaisesRegex(REUSE.CertificateReuseError, "timed out"):
                    self.original_run(["az"])
                command.assert_not_called()
        finally:
            REUSE.DEADLINE.reset(token)

    def test_cli_validates_new_material_and_rejects_invalid_arguments(self):
        arguments = [str(HELPER), "validate", "--fqdn", FQDN, "--directory", str(self.folder)]
        with patch.object(REUSE.sys, "argv", arguments):
            self.assertEqual(REUSE.main(), 0)
        with patch.object(REUSE.sys, "argv", arguments), patch.object(REUSE, "validate_material", return_value=False):
            self.assertEqual(REUSE.main(), 1)

    def test_valid_certificate_with_matching_key_and_public_trust_is_reusable(self):
        self.assertTrue(REUSE.validate_material(self.folder, FQDN))

    def test_near_expiry_and_expired_material_need_renewal(self):
        for days in (65, 95):
            with self.subTest(days=days):
                self.assertFalse(
                    REUSE.validate_material(self.folder, FQDN, datetime.now(timezone.utc) + timedelta(days=days))
                )

    def test_not_yet_valid_material_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not yet valid"):
            REUSE.validate_material(self.folder, FQDN, datetime.now(timezone.utc) - timedelta(days=1))

    def test_wrong_hostname_and_wildcard_are_rejected(self):
        for name in ("wrong", "wildcard"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "exact requested DNS"):
                REUSE.validate_material(self.root / name, FQDN)

    def test_untrusted_chain_is_rejected(self):
        with patch.dict(os.environ, {"SSL_CERT_FILE": str(self.folder / "missing-ca.pem")}, clear=False):
            with self.assertRaises(RuntimeError):
                REUSE.validate_material(self.folder, FQDN)

    def test_mismatched_or_missing_private_key_is_rejected(self):
        shutil.copyfile(self.root / "wrong/privkey.pem", self.folder / "privkey.pem")
        with self.assertRaisesRegex(ValueError, "do not match"):
            REUSE.validate_material(self.folder, FQDN)
        (self.folder / "privkey.pem").unlink()
        with self.assertRaises(RuntimeError):
            REUSE.validate_material(self.folder, FQDN)


if __name__ == "__main__":
    unittest.main()
