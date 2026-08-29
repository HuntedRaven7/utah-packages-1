#!/usr/bin/env python3
"""Fetch and verify direct-upstream sources, failing closed on any mismatch.

The configuration intentionally uses JSON so the standard Python runtime on
GitHub-hosted runners is sufficient.  A package entry has ``name``, ``url``,
and a required ``sha512``.  An optional ``sha256_url`` points at an upstream
checksum manifest; the downloaded archive must appear in that manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fetch(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "hummingbird-github-source-pipeline/1"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def verify_signature(package: dict, target: Path, directory: Path) -> None:
    key, signature_url = package.get("gpg_key"), package.get("signature_url")
    if bool(key) != bool(signature_url):
        raise ValueError("gpg_key and signature_url must be configured together")
    if not key:
        return
    signature = directory / f"{target.name}.asc"
    fetch(signature_url, signature)
    key_path = Path(key)
    if not key_path.is_file():
        raise ValueError(f"configured GPG key does not exist: {key_path}")
    with __import__("tempfile").TemporaryDirectory(prefix="source-pipeline-gpg-") as home:
        environment = {"GNUPGHOME": home}
        subprocess.run(["gpg", "--batch", "--import", str(key_path)], check=True, env=environment, capture_output=True)
        subprocess.run(["gpg", "--batch", "--verify", str(signature), str(target)], check=True, env=environment, capture_output=True)


def selected(config: dict, name: str | None) -> list[dict]:
    packages = config.get("packages", [])
    if name is None:
        return packages
    matches = [package for package in packages if package.get("name") == name]
    if not matches:
        raise SystemExit(f"package is not configured for direct upstream tracking: {name}")
    return matches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", nargs="?")
    parser.add_argument("--config", type=Path, default=Path("config/upstream-sources.json"))
    parser.add_argument("--output", type=Path, default=Path("sources"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports/source-pipeline"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    succeeded = True
    for package in selected(config, args.package):
        missing = {"name", "url", "sha512"} - package.keys()
        if missing:
            raise SystemExit(f"invalid direct-source entry: missing {', '.join(sorted(missing))}")
        name, url, expected = package["name"], package["url"], package["sha512"].lower()
        target_dir = args.output / name
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = package.get("filename") or Path(urllib.parse.urlparse(url).path).name or f"{name}.source"
        candidate = target_dir / f"{filename}.candidate"
        report: dict[str, object] = {"package": name, "url": url, "checked_at": datetime.now(UTC).isoformat()}
        try:
            fetch(url, candidate)
            actual = digest(candidate, "sha512")
            if actual != expected:
                raise ValueError(f"SHA-512 mismatch: expected {expected}, got {actual}")
            verify_signature(package, candidate, target_dir)
            if checksum_url := package.get("sha256_url"):
                checksum_file = target_dir / "upstream.sha256"
                fetch(checksum_url, checksum_file)
                expected_sha256 = digest(candidate, "sha256")
                if expected_sha256 not in checksum_file.read_text(errors="replace"):
                    raise ValueError("download is absent from the upstream SHA-256 manifest")
            final = target_dir / filename
            candidate.replace(final)
            report.update({"result": "accepted", "sha512": actual, "file": str(final)})
        except Exception as error:  # Do not replace an accepted source.
            candidate.unlink(missing_ok=True)
            succeeded = False
            report.update({"result": "rejected", "error": str(error)})
        args.report_dir.mkdir(parents=True, exist_ok=True)
        (args.report_dir / f"{name}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, sort_keys=True))
    return 0 if succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
