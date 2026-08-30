#!/usr/bin/env python3
"""Resolve the Hummingbird-only Utah runtime transaction the factory must satisfy."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path


def package_section(document: dict, section: str) -> list[str]:
    value = document.get(section, {})
    packages = value.get("packages", [])
    if not isinstance(packages, list) or not all(isinstance(p, str) for p in packages):
        raise ValueError(f"[{section}].packages must be an array of strings")
    return packages


def load_policy(policy_path: Path) -> dict:
    return tomllib.loads(policy_path.read_text())


def base_image(policy: dict) -> str:
    image = policy.get("base", {}).get("image", "")
    if not isinstance(image, str) or "@sha256:" not in image:
        raise ValueError("[base].image must be an OCI reference pinned by sha256 digest")
    return image


def resolve(bluefin_path: Path, policy_path: Path) -> list[str]:
    bluefin = tomllib.loads(bluefin_path.read_text())
    policy = load_policy(policy_path)
    base_image(policy)

    sections = policy.get("bluefin", {}).get("sections", [])
    if not isinstance(sections, list) or not all(isinstance(s, str) for s in sections):
        raise ValueError("[bluefin].sections must be an array of strings")
    if not sections:
        raise ValueError("runtime contract has no Bluefin sections")

    unavailable = set(package_section(policy, "unavailable"))
    requested: list[str] = []
    for section in sections:
        if section not in bluefin:
            raise ValueError(f"Bluefin manifest has no [{section}] section")
        requested.extend(package_section(bluefin, section))
    requested.extend(package_section(policy, "utah"))

    unknown_exceptions = unavailable - set(requested)
    if unknown_exceptions:
        names = ", ".join(sorted(unknown_exceptions))
        raise ValueError(f"unavailable packages are not requested by the contract: {names}")

    # Preserve declaration order for readable solver logs while removing names
    # repeated across Bluefin and Utah sections.
    return list(dict.fromkeys(name for name in requested if name not in unavailable))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bluefin", type=Path)
    parser.add_argument("policy", type=Path)
    parser.add_argument("--json", action="store_true", help="emit a JSON array")
    parser.add_argument("--check", action="store_true", help="validate without listing")
    parser.add_argument("--base-image", action="store_true", help="emit the pinned base image")
    args = parser.parse_args()

    try:
        policy = load_policy(args.policy)
        image = base_image(policy)
        packages = resolve(args.bluefin, args.policy)
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not packages:
        print("ERROR: runtime contract resolved to no packages", file=sys.stderr)
        return 1

    if args.base_image:
        print(image)
    elif args.check:
        print(f"validated runtime contract: {len(packages)} packages against {image}")
    elif args.json:
        print(json.dumps(packages))
    else:
        print("\n".join(packages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
