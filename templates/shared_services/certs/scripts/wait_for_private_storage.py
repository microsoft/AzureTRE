#!/usr/bin/env python3
"""Wait for consecutive private DNS and verified TLS checks on a storage endpoint."""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import time


PROBE_TIMEOUT_SECONDS = 10
TIMEOUT_SECONDS = 300
REQUIRED_SUCCESSES = 7
INTERVAL_SECONDS = 5


def probe(hostname, expected_ip):
    """Connect only when every DNS answer matches the private endpoint address."""
    try:
        answers = {
            ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        }
        if answers != {ipaddress.ip_address(expected_ip)}:
            return False, "DNS does not exclusively resolve to the expected private endpoint"
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        with socket.create_connection((expected_ip, 443), timeout=5) as connection:
            with context.wrap_socket(connection, server_hostname=hostname):
                return True, "private DNS and TLS verification passed"
    except (OSError, ValueError) as error:
        return False, f"DNS or TLS check failed ({type(error).__name__})"


def run_probe(hostname, expected_ip, timeout):
    # A child process bounds getaddrinfo(), which has no per-call timeout.
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--probe",
                "--hostname",
                hostname,
                "--expected-ip",
                expected_ip,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "DNS or TLS check timed out"
    if result.returncode not in (0, 1):
        return False, "DNS or TLS check process failed"
    try:
        value = json.loads(result.stdout)
        if type(value.get("ready")) is not bool or not isinstance(value.get("reason"), str):
            raise ValueError("Invalid probe result")
    except (AttributeError, ValueError):
        return False, "DNS or TLS check returned an invalid result"
    if value["ready"] != (result.returncode == 0):
        return False, "DNS or TLS check returned an inconsistent result"
    return value["ready"], value["reason"]


def wait_for_private_storage(
    hostname, expected_ip, timeout=TIMEOUT_SECONDS, required_successes=REQUIRED_SUCCESSES, interval=INTERVAL_SECONDS
):
    deadline = time.monotonic() + timeout
    successes = 0
    last_reason = "no completed check"
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        ready, last_reason = run_probe(hostname, expected_ip, min(PROBE_TIMEOUT_SECONDS, remaining))
        if time.monotonic() >= deadline:
            break
        successes = successes + 1 if ready else 0
        print(f"Storage readiness: {last_reason} ({successes}/{required_successes} consecutive checks)", flush=True)
        if successes >= required_successes:
            return
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise TimeoutError(
        f"Private storage endpoint was not ready within {timeout} seconds: {last_reason}. Check private DNS and endpoint connectivity before retrying."
    )


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hostname", default=os.environ.get("STORAGE_HOST"))
    parser.add_argument("--expected-ip", default=os.environ.get("STORAGE_PRIVATE_IP"))
    parser.add_argument("--probe", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.hostname or any(c.isspace() for c in args.hostname) or any(c in args.hostname for c in "/:\\"):
        parser.error("A storage DNS hostname is required")
    try:
        address = ipaddress.ip_address(args.expected_ip)
    except ValueError:
        parser.error("A private endpoint IP address is required")
    if (
        not address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_unspecified
        or address.is_multicast
    ):
        parser.error("The expected address must be a private endpoint IP address")
    return args


def main():
    args = parse_args()
    if args.probe:
        ready, reason = probe(args.hostname, args.expected_ip)
        print(json.dumps({"ready": ready, "reason": reason}))
        return 0 if ready else 1
    try:
        wait_for_private_storage(args.hostname, args.expected_ip)
    except (OSError, TimeoutError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
