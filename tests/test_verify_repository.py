#!/usr/bin/env python3

from pathlib import Path
import tempfile
import unittest

from tools.verify_repository import verify_repository

ROOT = Path(__file__).resolve().parent.parent


class VerifyRepositoryTests(unittest.TestCase):
    def test_rejects_missing_repodata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "foo-1.0.rpm").write_text("dummy")
            with self.assertRaisesRegex(ValueError, "missing repodata"):
                verify_repository(repo, ["foo"])

    def test_rejects_missing_expected_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "repodata").mkdir()
            (repo / "repodata" / "repomd.xml").write_text("<repomd/>")
            (repo / "foo-1.0.rpm").write_text("dummy")
            with self.assertRaisesRegex(ValueError, "missing package: bar"):
                verify_repository(repo, ["foo", "bar"], rpm_names=["foo-1.0.rpm"])

    def test_accepts_valid_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "repodata").mkdir()
            (repo / "repodata" / "repomd.xml").write_text("<repomd/>")
            (repo / "foo-1.0.rpm").write_text("dummy")
            self.assertTrue(
                verify_repository(repo, ["foo"], rpm_names=["foo-1.0.rpm"])
            )


if __name__ == "__main__":
    unittest.main()
