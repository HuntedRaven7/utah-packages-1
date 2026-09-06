#!/usr/bin/env python3

from pathlib import Path
import unittest

from tools.build_manifest import (
    PackageBuildResult,
    FactoryManifest,
    summarize,
)

ROOT = Path(__file__).resolve().parent.parent


def successful_result(name: str) -> PackageBuildResult:
    return PackageBuildResult(
        package=name,
        status="success",
        stage=0,
        srpm_name=f"{name}-1.0.src.rpm",
        srpm_sha512="0" * 128,
        rpms=[{"name": f"{name}-1.0.x86_64.rpm", "sha512": "1" * 128, "nevra": f"{name}-1.0-1.x86_64"}],
    )


def failed_result(name: str) -> PackageBuildResult:
    return PackageBuildResult(
        package=name,
        status="failure",
        stage=0,
        srpm_name="",
        srpm_sha512="",
        rpms=[],
    )


class BuildManifestTests(unittest.TestCase):
    def test_summary_rejects_missing_package(self):
        with self.assertRaisesRegex(ValueError, "missing: beta"):
            summarize(["alpha", "beta"], [successful_result("alpha")])

    def test_summary_rejects_failed_package(self):
        with self.assertRaisesRegex(ValueError, "failed: alpha"):
            summarize(["alpha"], [failed_result("alpha")])

    def test_summary_rejects_duplicate_package(self):
        with self.assertRaisesRegex(ValueError, "duplicate: alpha"):
            summarize(["alpha"], [successful_result("alpha"), successful_result("alpha")])

    def test_summary_accepts_exact_complete_inventory(self):
        manifest = summarize(
            ["alpha", "beta"],
            [successful_result("alpha"), successful_result("beta")],
        )
        self.assertEqual(manifest.completed_source_packages, 2)
        self.assertEqual(manifest.failed_source_packages, 0)
        self.assertEqual(len(manifest.results), 2)


if __name__ == "__main__":
    unittest.main()
