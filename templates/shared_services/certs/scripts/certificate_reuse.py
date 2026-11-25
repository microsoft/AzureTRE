#!/usr/bin/env python3
"""Reuse an issued certificate from its existing core Key Vault name."""

import argparse
import base64
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
from itertools import groupby
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit

BOOTSTRAP_PFX = Path(__file__).resolve().parents[1] / "terraform/bootstrap.pfx"
RENEW_BEFORE_SECONDS = 30 * 24 * 60 * 60
ISSUANCE_REQUIRED = 3
LOOKUP_TIMEOUT_SECONDS = 180
DEADLINE = ContextVar("certificate_lookup_deadline", default=None)


class CertificateReuseError(RuntimeError):
    """A diagnostic that contains no certificate-secret values."""


def run(arguments):
    timeout = LOOKUP_TIMEOUT_SECONDS
    if DEADLINE.get() is not None:
        timeout = min(timeout, DEADLINE.get() - time.monotonic())
    if timeout <= 0:
        raise CertificateReuseError("Certificate lookup timed out")
    try:
        return subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=True).stdout
    except subprocess.CalledProcessError:
        raise CertificateReuseError(
            "Certificate command failed. Check vault access and operation diagnostics"
        ) from None
    except subprocess.TimeoutExpired:
        raise CertificateReuseError("Certificate lookup timed out") from None


def azure(*arguments):
    return json.loads(run(["az", *arguments, "--only-show-errors", "--output", "json"]))


def version_id(value, vault_url, name, kind):
    """Accept only an exact version of the configured object in the expected vault."""
    parsed = urlsplit(value)
    expected = urlsplit(vault_url)
    pieces = parsed.path.split("/")
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != expected.netloc.lower()
        or parsed.query
        or parsed.fragment
        or len(pieces) != 4
        or pieces[1] != kind
        or pieces[2].lower() != name.lower()
        or not re.fullmatch(r"[a-fA-F0-9]{32}", pieces[3])
    ):
        raise CertificateReuseError("Certificate lookup returned an unexpected vault, name or version")
    return pieces[3]


def creation_time(item):
    value = item["attributes"]["created"]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CertificateReuseError("Certificate version has no creation timezone")
    return parsed.timestamp()


def fingerprint(certificate, directory):
    if certificate["attributes"].get("enabled") is not True:
        raise CertificateReuseError("The certificate version is disabled")
    public = directory / "certificate.der"
    public.unlink(missing_ok=True)
    run(
        [
            "az",
            "keyvault",
            "certificate",
            "download",
            "--id",
            certificate["id"],
            "--encoding",
            "DER",
            "--file",
            str(public),
            "--only-show-errors",
        ]
    )
    return hashlib.sha256(public.read_bytes()).hexdigest()


def bootstrap_fingerprint(directory):
    """Identify the same temporary certificate that Terraform imports."""
    public = directory / "bootstrap.pem"
    der = directory / "bootstrap.der"
    run(
        [
            "openssl",
            "pkcs12",
            "-in",
            str(BOOTSTRAP_PFX),
            "-passin",
            "pass:0000000000",
            "-nokeys",
            "-out",
            str(public),
        ]
    )
    run(["openssl", "x509", "-in", str(public), "-outform", "DER", "-out", str(der)])
    return hashlib.sha256(der.read_bytes()).hexdigest()


def select_certificate(latest, vault, vault_url, name, directory):
    version_id(latest["id"], vault_url, name, "certificates")
    bootstrap_digest = bootstrap_fingerprint(directory)
    digest = fingerprint(latest, directory)
    if digest != bootstrap_digest:
        return latest, digest

    # Azure CLI consumes all service pages. Do not limit or trust the returned order.
    versions = azure("keyvault", "certificate", "list-versions", "--vault-name", vault, "--name", name)
    if not isinstance(versions, list) or not versions:
        raise CertificateReuseError("Certificate version history is incomplete")
    ids = [item["id"] for item in versions]
    if latest["id"] not in ids or len(set(ids)) != len(ids):
        raise CertificateReuseError("Certificate version history is inconsistent")
    for item in versions:
        version_id(item["id"], vault_url, name, "certificates")
    ordered = sorted(versions, key=creation_time, reverse=True)
    for _, group in groupby(ordered, key=creation_time):
        issued = []
        for item in group:
            if item["id"] == latest["id"]:
                continue
            certificate = azure("keyvault", "certificate", "show", "--id", item["id"])
            if certificate["id"] != item["id"]:
                raise CertificateReuseError("Certificate version changed during lookup")
            digest = fingerprint(certificate, directory)
            if digest != bootstrap_digest:
                issued.append((certificate, digest))
        if len(issued) > 1:
            raise CertificateReuseError("Cannot determine the newest issued certificate version")
        if issued:
            # Assess this version even if invalid. Never fall back to an older issued certificate.
            return issued[0]
    return None, None


def validate_material(directory, fqdn, now=None, *, allow_hostname_change=False):
    """Validate material; return whether it covers the hostname and is reusable."""
    leaf = directory / "leaf.pem"
    fullchain = directory / "fullchain.pem"
    key = directory / "privkey.pem"
    run(["openssl", "x509", "-in", str(fullchain), "-out", str(leaf)])
    san = run(["openssl", "x509", "-in", str(leaf), "-noout", "-ext", "subjectAltName"])
    names = re.findall(r"DNS:([^,\s]+)", san)
    hostname_matches = fqdn.lower() in [name.lower() for name in names]
    if not hostname_matches and not allow_hostname_change:
        raise ValueError("Certificate does not contain the exact requested DNS name")
    dates = run(["openssl", "x509", "-in", str(leaf), "-noout", "-dates"])
    bounds = dict(line.split("=", 1) for line in dates.strip().splitlines())
    start, end = [
        datetime.strptime(bounds[k], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        for k in ("notBefore", "notAfter")
    ]
    now = now or datetime.now(timezone.utc)
    if start > now:
        raise ValueError("Certificate is not yet valid")
    certificate_key = run(["openssl", "x509", "-in", str(leaf), "-noout", "-pubkey"])
    private_key = run(["openssl", "pkey", "-in", str(key), "-pubout"])
    if certificate_key.strip() != private_key.strip():
        raise ValueError("Certificate and private key do not match")
    # Verify the chain at an instant within the certificate validity period.
    # Expired but otherwise valid material requests renewal below.
    verify_time = now.timestamp() if now < end else end.timestamp() - 1
    # An existing certificate for another hostname still needs a valid chain and key.
    # Newly issued material must always match the requested hostname.
    hostname_check = ["-verify_hostname", fqdn] if hostname_matches else []
    run(
        [
            "openssl",
            "verify",
            "-purpose",
            "sslserver",
            *hostname_check,
            "-attime",
            str(int(verify_time)),
            "-untrusted",
            str(fullchain),
            str(leaf),
        ]
    )
    return hostname_matches and (end - now).total_seconds() > RENEW_BEFORE_SECONDS


def restore(vault, name, fqdn, directory):
    token = DEADLINE.set(time.monotonic() + LOOKUP_TIMEOUT_SECONDS)
    try:
        return restore_before_deadline(vault, name, fqdn, directory)
    finally:
        DEADLINE.reset(token)


def restore_before_deadline(vault, name, fqdn, directory):
    if not re.fullmatch(r"[A-Za-z0-9-]+", vault) or not re.fullmatch(r"[A-Za-z0-9-]+", name):
        raise CertificateReuseError("Invalid vault or certificate name")
    suffix = azure("cloud", "show")["suffixes"]["keyvaultDns"]
    if not re.fullmatch(r"\.[A-Za-z0-9.-]+", suffix):
        raise CertificateReuseError("Invalid Key Vault endpoint for the current Azure cloud")
    vault_url = f"https://{vault}{suffix}"
    # Terraform must create or recover the object first. A lookup error is not a cache miss.
    latest = azure("keyvault", "certificate", "show", "--vault-name", vault, "--name", name)
    certificate, digest = select_certificate(latest, vault, vault_url, name, directory)
    reusable = False
    if certificate is not None:
        version = version_id(certificate["id"], vault_url, name, "certificates")
        if version_id(certificate["sid"], vault_url, name, "secrets") != version:
            raise CertificateReuseError("Certificate and secret versions differ")
        secret = azure("keyvault", "secret", "show", "--id", certificate["sid"])
        if secret["id"] != certificate["sid"] or secret["attributes"].get("enabled") is not True:
            raise CertificateReuseError("The certificate secret is disabled or has an unexpected version")
        content_type = secret.get("contentType")
        if content_type == "application/x-pem-file":
            material = directory / "reuse.pem"
            material.write_text(secret["value"])
            certificates = re.findall(
                r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", secret["value"], re.DOTALL
            )
            if not certificates:
                raise CertificateReuseError("The certificate secret contains no certificates")
            (directory / "fullchain.pem").write_text("\n".join(certificates) + "\n")
            run(["openssl", "pkey", "-in", str(material), "-out", str(directory / "privkey.pem")])
        elif content_type == "application/x-pkcs12":
            material = directory / "reuse.pfx"
            material.write_bytes(base64.b64decode(secret["value"], validate=True))
            run(
                [
                    "openssl",
                    "pkcs12",
                    "-in",
                    str(material),
                    "-passin",
                    "pass:",
                    "-nokeys",
                    "-out",
                    str(directory / "fullchain.pem"),
                ]
            )
            run(
                [
                    "openssl",
                    "pkcs12",
                    "-in",
                    str(material),
                    "-passin",
                    "pass:",
                    "-nocerts",
                    "-nodes",
                    "-out",
                    str(directory / "privkey.pem"),
                ]
            )
        else:
            raise CertificateReuseError("The certificate secret has an unsupported content type")
        reusable = validate_material(directory, fqdn, allow_hostname_change=True)
        public = directory / "selected.der"
        run(["openssl", "x509", "-in", str(directory / "leaf.pem"), "-outform", "DER", "-out", str(public)])
        if hashlib.sha256(public.read_bytes()).hexdigest() != digest:
            raise CertificateReuseError("The certificate secret does not match its public certificate")
    current = azure("keyvault", "certificate", "show", "--vault-name", vault, "--name", name)
    if current["id"] != latest["id"] or current["attributes"].get("enabled") is not True:
        raise CertificateReuseError("The active certificate changed during lookup")
    if reusable:
        # The shell imports older versions and converts PEM secrets to PFX for Application Gateway.
        (directory / "reuse.json").write_text(
            json.dumps(
                {
                    "is_current": certificate["id"] == latest["id"],
                    "secret_id": certificate["sid"],
                    "content_type": content_type,
                }
            )
        )
        print(f"Reusing certificate {name}, SHA-256 fingerprint {digest}; no ACME request required")
    else:
        print(
            "Certificate issuance required: "
            + ("hostname is not covered or renewal is due" if certificate else "only bootstrap versions exist")
        )
    return reusable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("restore", "validate"))
    parser.add_argument("--vault")
    parser.add_argument("--cert-name")
    parser.add_argument("--fqdn", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.action == "restore":
            if not args.vault or not args.cert_name:
                parser.error("--vault and --cert-name are required for restore")
            return 0 if restore(args.vault, args.cert_name, args.fqdn, args.directory) else ISSUANCE_REQUIRED
        if not validate_material(args.directory, args.fqdn):
            raise CertificateReuseError("The issued certificate is already due for renewal")
        return 0
    except CertificateReuseError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (ValueError, KeyError, TypeError, OSError):
        print("Certificate validation failed. Check the hostname, key, validity and vault response", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
