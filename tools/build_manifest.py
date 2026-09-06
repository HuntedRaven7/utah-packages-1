#!/usr/bin/env python3
"""Reproducible package build results and factory manifest tooling."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


def _sha512_file(path: Path) -> str:
    h = hashlib.sha512()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_nevra(rpm_path: Path) -> str:
    try:
        proc = subprocess.run(
            ["rpm", "-qp", "--qf", "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}", str(rpm_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return rpm_path.stem


@dataclass
class PackageBuildResult:
    package: str
    status: str
    stage: int = 0
    srpm_name: str = ""
    srpm_sha512: str = ""
    rpms: list[dict] = field(default_factory=list)
    node: str = ""
    duration: float = 0.0
    retry_count: int = 0
    source_hashes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> PackageBuildResult:
        return cls(**data)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class FactoryManifest:
    completed_source_packages: int
    failed_source_packages: int
    results: list[PackageBuildResult]

    def to_dict(self) -> dict:
        return {
            "completed_source_packages": self.completed_source_packages,
            "failed_source_packages": self.failed_source_packages,
            "results": [r.to_dict() for r in self.results],
        }


def summarize(expected: list[str], results: list[PackageBuildResult]) -> FactoryManifest:
    seen = set()
    for r in results:
        if r.package in seen:
            raise ValueError(f"duplicate: {r.package}")
        seen.add(r.package)

    for r in results:
        if r.status != "success":
            raise ValueError(f"failed: {r.package}")

    expected_set = set(expected)
    result_set = {r.package for r in results}
    missing = sorted(expected_set - result_set)
    if missing:
        raise ValueError(f"missing: {', '.join(missing)}")

    return FactoryManifest(
        completed_source_packages=len(results),
        failed_source_packages=0,
        results=sorted(results, key=lambda r: r.package),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    pkg_parser = subparsers.add_parser("package")
    pkg_parser.add_argument("--package", required=True)
    pkg_parser.add_argument("--stage", type=int, default=0)
    pkg_parser.add_argument("--srpm", type=Path)
    pkg_parser.add_argument("--rpm-dir", type=Path)
    pkg_parser.add_argument("--output", type=Path, required=True)

    stage_parser = subparsers.add_parser("stage")
    stage_parser.add_argument("--expected", type=Path, required=True)
    stage_parser.add_argument("--results", type=Path, required=True)
    stage_parser.add_argument("--output", type=Path, required=True)

    final_parser = subparsers.add_parser("final")
    final_parser.add_argument("--expected", type=Path, required=True)
    final_parser.add_argument("--stage-manifests", type=Path, required=True)
    final_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    if args.command == "package":
        srpm_name = ""
        srpm_sha = ""
        if args.srpm and args.srpm.is_file():
            srpm_name = args.srpm.name
            srpm_sha = _sha512_file(args.srpm)

        rpms = []
        if args.rpm_dir and args.rpm_dir.is_dir():
            for rpm_file in sorted(args.rpm_dir.glob("**/*.rpm")):
                if rpm_file.name.endswith(".src.rpm"):
                    continue
                rpms.append({
                    "name": rpm_file.name,
                    "sha512": _sha512_file(rpm_file),
                    "nevra": _get_nevra(rpm_file),
                })

        res = PackageBuildResult(
            package=args.package,
            status="success",
            stage=args.stage,
            srpm_name=srpm_name,
            srpm_sha512=srpm_sha,
            rpms=rpms,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(res.to_dict(), indent=2) + "\n")

    elif args.command == "stage":
        expected_raw = json.loads(args.expected.read_text())
        expected = expected_raw if isinstance(expected_raw, list) else [p["name"] for p in expected_raw.get("packages", [])]
        results = []
        for res_file in sorted(args.results.glob("*.json")):
            results.append(PackageBuildResult.from_dict(json.loads(res_file.read_text())))
        manifest = summarize(expected, results)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n")

    elif args.command == "final":
        expected_raw = json.loads(args.expected.read_text())
        expected = expected_raw if isinstance(expected_raw, list) else [p["name"] for p in expected_raw.get("packages", [])]
        results = []
        for stage_file in sorted(args.stage_manifests.glob("*.json")):
            stage_data = json.loads(stage_file.read_text())
            for r in stage_data.get("results", []):
                results.append(PackageBuildResult.from_dict(r))
        manifest = summarize(expected, results)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
