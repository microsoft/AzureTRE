#!/usr/bin/env python3
"""Retain verified certificates in the core vault across service replacement."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

CACHE_PREFIX = "tre-acme-"
CACHE_TAG = "certificate-v1"
RENEW_BEFORE_SECONDS = 30 * 24 * 60 * 60
CACHE_MISS = 3


class CertificateNotFound(RuntimeError):
    """The vault returned its explicit certificate-not-found response."""


def cache_name(fqdn):
    return CACHE_PREFIX + hashlib.sha256(fqdn.lower().encode("ascii")).hexdigest()


def run(arguments):
    """Do not expose command output or arguments when a secret operation fails."""
    try:
        return subprocess.run(arguments, capture_output=True, text=True, timeout=180, check=True).stdout
    except subprocess.CalledProcessError as error:
        code = re.search(r"^\s*(?:ERROR: )?\(([A-Za-z0-9]+)\)", error.stderr or "", re.MULTILINE)
        if code and code[1] == "CertificateNotFound":
            raise CertificateNotFound("Certificate not found") from None
        raise RuntimeError(f"Certificate command failed ({code[1] if code else 'see operation diagnostics'})") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError("Certificate command timed out") from None


def azure(*arguments):
    return json.loads(run(["az", *arguments, "--only-show-errors", "--output", "json"]))


def validate_name(name):
    if name.lower().startswith(CACHE_PREFIX):
        raise ValueError(f"Certificate names starting with {CACHE_PREFIX} are reserved for the retained cache")


def validate_material(directory, fqdn, now=None):
    """Check exact SAN, public trust, validity and the private key before reuse."""
    leaf = directory / "leaf.pem"
    fullchain = directory / "fullchain.pem"
    key = directory / "privkey.pem"
    run(["openssl", "x509", "-in", str(fullchain), "-out", str(leaf)])
    san = run(["openssl", "x509", "-in", str(leaf), "-noout", "-ext", "subjectAltName"])
    names = re.findall(r"DNS:([^,\s]+)", san)
    if fqdn.lower() not in [name.lower() for name in names]:
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
    run(
        [
            "openssl",
            "verify",
            "-purpose",
            "sslserver",
            "-verify_hostname",
            fqdn,
            "-attime",
            str(int(verify_time)),
            "-untrusted",
            str(fullchain),
            str(leaf),
        ]
    )
    return (end - now).total_seconds() > RENEW_BEFORE_SECONDS


def restore(vault, fqdn, directory):
    name = cache_name(fqdn)
    try:
        certificate = azure("keyvault", "certificate", "show", "--vault-name", vault, "--name", name)
    except CertificateNotFound:
        # A deleted cache is an explicit administrative state, not permission to issue again.
        try:
            azure("keyvault", "certificate", "show-deleted", "--vault-name", vault, "--name", name)
        except CertificateNotFound:
            print("No retained certificate. Production issuance is required.")
            return False
        raise RuntimeError("The retained certificate is deleted. Recover it before retrying")
    if certificate.get("attributes", {}).get("enabled") is not True:
        raise ValueError("The retained certificate is disabled")
    if certificate.get("tags", {}).get("tre-cache") != CACHE_TAG:
        raise ValueError("The retained certificate has no recognised ownership tag")
    if certificate.get("tags", {}).get("fqdn") != fqdn.lower():
        raise ValueError("The retained certificate belongs to another DNS name")
    content_type = certificate.get("policy", {}).get("secretProperties", {}).get("contentType")
    if content_type not in ("application/x-pem-file", "application/x-pkcs12"):
        raise ValueError("The retained certificate has an unsupported or missing content type")
    is_pem = content_type == "application/x-pem-file"
    # Download the exact version in its stored format. PEM secrets contain text;
    # PFX secrets contain base64 data. Downloading does not convert the format.
    material = directory / ("retained.pem" if is_pem else "retained.pfx")
    run(
        [
            "az",
            "keyvault",
            "secret",
            "download",
            "--id",
            certificate["sid"],
            "--file",
            str(material),
            "--encoding",
            "utf-8" if is_pem else "base64",
            "--only-show-errors",
        ]
    )
    if is_pem:
        certificates = re.findall(
            r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", material.read_text(), re.DOTALL
        )
        if not certificates:
            raise ValueError("The retained PEM contains no certificates")
        (directory / "fullchain.pem").write_text("\n".join(certificates) + "\n")
        run(["openssl", "pkey", "-in", str(material), "-out", str(directory / "privkey.pem")])
    else:
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
    if not validate_material(directory, fqdn):
        print("The retained certificate is due for renewal. Production issuance is required.")
        return False
    print(f"Reusing retained certificate {name}, thumbprint {certificate['x509ThumbprintHex']}")
    return True


def store(vault, fqdn, directory):
    if not validate_material(directory, fqdn):
        raise ValueError("The issued certificate is already due for renewal")
    # A PEM import includes the private key and complete chain. The CLI reads a private file.
    material = directory / "cache-import.pem"
    material.write_text((directory / "privkey.pem").read_text() + (directory / "fullchain.pem").read_text())
    try:
        certificate = azure(
            "keyvault",
            "certificate",
            "import",
            "--vault-name",
            vault,
            "--name",
            cache_name(fqdn),
            "--file",
            str(material),
            "--tags",
            f"tre-cache={CACHE_TAG}",
            f"fqdn={fqdn.lower()}",
        )
    finally:
        material.unlink(missing_ok=True)
    print(f"Retained issued certificate {cache_name(fqdn)}, thumbprint {certificate['x509ThumbprintHex']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate-name", "restore", "store"))
    parser.add_argument("--cert-name", required=True)
    parser.add_argument("--vault")
    parser.add_argument("--fqdn")
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        validate_name(args.cert_name)
        if args.action == "validate-name":
            return 0
        if not args.vault or not args.fqdn or not args.directory:
            parser.error("--vault, --fqdn and --directory are required")
        if args.action == "restore":
            return 0 if restore(args.vault, args.fqdn, args.directory) else CACHE_MISS
        store(args.vault, args.fqdn, args.directory)
        return 0
    except (ValueError, KeyError, OSError, RuntimeError):
        # Exception arguments can contain secret command results or certificate material.
        print(
            "Certificate reuse failed. Check vault access, cache ownership, validity and trust before retrying.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
