#!/usr/bin/env python3
"""Create direct-source candidates from imported RPM recipes.

This deliberately does not consult Fedora's lookaside cache. A candidate is
accepted only when the resolved Source0 is an upstream HTTP(S) URL and its
bytes can be downloaded directly. Everything else is reported for an explicit
maintainer decision rather than silently falling back to Rawhide.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


FEDORA_HOSTS = ("fedoraproject.org", "src.fedoraproject.org", "kojipkgs.fedoraproject.org")


def rpm_value(spec: Path, query: str) -> str:
    return subprocess.check_output(["rpmspec", "-q", "--qf", query, str(spec)], text=True).splitlines()[0]


def sources(spec: Path) -> list[tuple[int, str]]:
    parsed = subprocess.check_output(["rpmspec", "--parse", str(spec)], text=True, stderr=subprocess.STDOUT)
    return [(int(index or 0), url) for index, url in re.findall(r"^Source(\d*):\s*(\S+)\s*$", parsed, flags=re.MULTILINE)]


def sha512(url: str) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "hummingbird-github-bootstrap/1"})
    value = hashlib.sha512()
    with urllib.request.urlopen(request, timeout=120) as response:
        filename = Path(urllib.parse.urlparse(response.url).path).name
        for block in iter(lambda: response.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest(), filename


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--packages", type=Path, default=Path("packages"))
    parser.add_argument("--output", type=Path, default=Path("config/upstream-sources.json"))
    parser.add_argument("--report", type=Path, default=Path("reports/direct-source-bootstrap.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    packages = (root / args.packages).resolve()
    candidates, rejected = [], []
    for package in sorted(path for path in packages.iterdir() if path.is_dir()):
        specs = list(package.glob("*.spec"))
        if len(specs) != 1:
            rejected.append({"package": package.name, "reason": f"expected one spec, found {len(specs)}"})
            continue
        spec = specs[0]
        try:
            name, version = rpm_value(spec, "%{NAME}"), rpm_value(spec, "%{VERSION}")
            declared_sources = sources(spec)
            url = next((value for index, value in declared_sources if index == 0), None)
            if not url or not url.startswith(("http://", "https://")):
                raise ValueError("Source0 is not a direct HTTP(S) URL")
            if len(declared_sources) > 1:
                raise ValueError("additional Source entries require an explicit verified source-closure mapping")
            if urllib.parse.urlparse(url).hostname in FEDORA_HOSTS:
                raise ValueError("Source0 points at Fedora infrastructure, not the upstream")
            digest, filename = sha512(url)
            candidates.append({"name": name, "version": version, "url": url, "filename": filename, "sha512": digest})
        except Exception as error:
            rejected.append({"package": package.name, "spec": str(spec.relative_to(root)), "reason": str(error)})
    output, report = root / args.output, root / args.report
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"schema": 1, "packages": candidates}, indent=2) + "\n")
    report.write_text(json.dumps({"accepted": len(candidates), "rejected": rejected}, indent=2) + "\n")
    print(f"accepted direct sources: {len(candidates)}; needs explicit mapping: {len(rejected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
