"""Check certificate reuse using a local CA and mocked vault access."""

from datetime import datetime, timedelta, timezone
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HELPER = Path(__file__).resolve().parents[2] / "templates/shared_services/certs/scripts/certificate_cache.py"
SPEC = importlib.util.spec_from_file_location("certificate_cache", HELPER)
CACHE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CACHE)
FQDN = "nexus-tre.example.test"


class CertificateCacheTests(unittest.TestCase):
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

    @staticmethod
    def command(*args):
        subprocess.run(["openssl", *args], capture_output=True, check=True, timeout=20)

    def setUp(self):
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.folder = Path(temporary)
        for name in ("privkey.pem", "fullchain.pem"):
            shutil.copyfile(self.root / "valid" / name, self.folder / name)
        self.enterContext(patch.dict(os.environ, {"SSL_CERT_FILE": str(self.root / "ca.pem")}))
        self.metadata = {
            "attributes": {"enabled": True},
            "sid": "https://vault.test/secrets/retained/exact-version",
            "tags": {"tre-cache": CACHE.CACHE_TAG, "fqdn": FQDN},
            "x509ThumbprintHex": "ABC",
        }

    def test_valid_certificate_with_matching_key_and_public_trust_is_reusable(self):
        self.assertTrue(CACHE.validate_material(self.folder, FQDN))

    def test_near_expiry_and_expired_material_need_renewal(self):
        for days in (65, 95):
            with self.subTest(days=days):
                self.assertFalse(
                    CACHE.validate_material(self.folder, FQDN, datetime.now(timezone.utc) + timedelta(days=days))
                )

    def test_not_yet_valid_material_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not yet valid"):
            CACHE.validate_material(self.folder, FQDN, datetime.now(timezone.utc) - timedelta(days=1))

    def test_wrong_hostname_and_wildcard_are_rejected(self):
        for name in ("wrong", "wildcard"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "exact requested DNS"):
                CACHE.validate_material(self.root / name, FQDN)

    def test_untrusted_chain_is_rejected(self):
        with patch.dict(os.environ, {"SSL_CERT_FILE": str(self.folder / "missing-ca.pem")}, clear=False):
            with self.assertRaises(RuntimeError):
                CACHE.validate_material(self.folder, FQDN)

    def test_mismatched_or_missing_private_key_is_rejected(self):
        shutil.copyfile(self.root / "wrong/privkey.pem", self.folder / "privkey.pem")
        with self.assertRaisesRegex(ValueError, "do not match"):
            CACHE.validate_material(self.folder, FQDN)
        (self.folder / "privkey.pem").unlink()
        with self.assertRaises(RuntimeError):
            CACHE.validate_material(self.folder, FQDN)

    def test_cache_identity_depends_on_hostname_not_service_alias(self):
        self.assertEqual(CACHE.cache_name(FQDN), CACHE.cache_name(FQDN.upper()))
        self.assertNotEqual(CACHE.cache_name(FQDN), CACHE.cache_name("other.test"))
        self.assertLessEqual(len(CACHE.cache_name(FQDN)), 127)
        for name in ("nexus-ssl", "nexus-e2e-12345678"):
            CACHE.validate_name(name)
        with self.assertRaises(ValueError):
            CACHE.validate_name(CACHE.cache_name(FQDN).upper())

    def test_absent_cache_is_the_only_lookup_error_that_allows_issuance(self):
        with patch.object(CACHE, "azure", side_effect=CACHE.CertificateNotFound()) as call:
            self.assertFalse(CACHE.restore("vault", FQDN, self.folder))
        self.assertEqual(call.call_count, 2)
        for error in (
            RuntimeError("Forbidden"),
            RuntimeError("network failure"),
            FileNotFoundError("Azure CLI is missing"),
            ValueError("invalid JSON"),
        ):
            with self.subTest(error=error), patch.object(CACHE, "azure", side_effect=error):
                with self.assertRaises(type(error)):
                    CACHE.restore("vault", FQDN, self.folder)

    def test_deleted_disabled_or_unowned_cache_is_not_overwritten(self):
        with patch.object(CACHE, "azure", side_effect=[CACHE.CertificateNotFound(), {}]):
            with self.assertRaisesRegex(RuntimeError, "deleted"):
                CACHE.restore("vault", FQDN, self.folder)
        for replacement in (
            {"attributes": {"enabled": False}},
            {"tags": {}},
            {"tags": {"tre-cache": CACHE.CACHE_TAG, "fqdn": "other.test"}},
        ):
            metadata = self.metadata | replacement
            with patch.object(CACHE, "azure", return_value=metadata), self.assertRaises(ValueError):
                CACHE.restore("vault", FQDN, self.folder)

    def test_restore_downloads_exact_version_and_validates_real_pfx(self):
        original = CACHE.run
        calls = []

        def command(args):
            calls.append(args)
            if args[:4] == ["az", "keyvault", "secret", "download"]:
                shutil.copyfile(self.root / "valid.pfx", self.folder / "retained.pfx")
                return ""
            return original(args)

        with patch.object(CACHE, "azure", return_value=self.metadata), patch.object(CACHE, "run", side_effect=command):
            self.assertTrue(CACHE.restore("vault", FQDN, self.folder))
        self.assertIn(self.metadata["sid"], calls[0])
        self.assertNotIn("--name", calls[0])

    def test_store_checks_material_and_retains_before_alias_publication(self):
        def import_certificate(*args):
            self.assertEqual(args[:3], ("keyvault", "certificate", "import"))
            self.assertIn(CACHE.cache_name(FQDN), args)
            self.assertIn("fqdn=" + FQDN, args)
            material = Path(args[args.index("--file") + 1]).read_text()
            self.assertIn("PRIVATE KEY", material)
            self.assertIn("CERTIFICATE", material)
            return self.metadata

        with patch.object(CACHE, "azure", side_effect=import_certificate):
            CACHE.store("vault", FQDN, self.folder)
        self.assertFalse((self.folder / "cache-import.pem").exists())

    def test_failed_cache_store_removes_temporary_import_and_does_not_claim_success(self):
        with patch.object(CACHE, "azure", side_effect=RuntimeError("access denied")):
            with self.assertRaises(RuntimeError):
                CACHE.store("vault", FQDN, self.folder)
        self.assertFalse((self.folder / "cache-import.pem").exists())

    def test_command_errors_redact_secret_output_and_preserve_not_found_distinction(self):
        for detail, expected in (
            ("ERROR: (CertificateNotFound) missing", CACHE.CertificateNotFound),
            ("ERROR: (Forbidden) secret-password", RuntimeError),
            ("secret-private-key", RuntimeError),
        ):
            with patch.object(
                CACHE.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["az", "secret"], stderr=detail)
            ):
                with self.assertRaises(expected) as caught:
                    CACHE.run(["az", "secret"])
            self.assertNotIn("secret-password", str(caught.exception))
            self.assertNotIn("secret-private-key", str(caught.exception))
        with patch.object(CACHE.subprocess, "run", side_effect=subprocess.TimeoutExpired("private-command", 180)):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                CACHE.run(["az", "secret"])

    def test_cli_guard_rejects_reserved_alias_before_terraform(self):
        result = subprocess.run(
            ["python3", str(HELPER), "validate-name", "--cert-name", "tre-acme-reserved"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
