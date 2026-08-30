#!/usr/bin/env python3

from pathlib import Path
import tempfile
import unittest

from tools.runtime_contract import base_image, resolve


BASE_POLICY = (
    "[base]\n"
    "image = \"quay.io/example/base@sha256:"
    + "0" * 64
    + "\"\n"
)


class RuntimeContractTests(unittest.TestCase):
    def write(self, root: Path, name: str, content: str) -> Path:
        path = root / name
        path.write_text(content)
        return path

    def test_resolves_sections_extras_and_exceptions_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bluefin = self.write(
                root,
                "bluefin.toml",
                "[fedora]\npackages = [\"one\", \"shared\", \"skip\"]\n"
                "[multimedia]\npackages = [\"codec\", \"shared\"]\n",
            )
            policy = self.write(
                root,
                "policy.toml",
                BASE_POLICY
                + "[bluefin]\nsections = [\"fedora\", \"multimedia\"]\n"
                "[utah]\npackages = [\"desktop\", \"shared\"]\n"
                "[unavailable]\npackages = [\"skip\"]\n",
            )
            self.assertEqual(
                resolve(bluefin, policy),
                ["one", "shared", "codec", "desktop"],
            )

    def test_rejects_exception_not_present_in_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bluefin = self.write(root, "bluefin.toml", "[fedora]\npackages = [\"one\"]\n")
            policy = self.write(
                root,
                "policy.toml",
                BASE_POLICY
                + "[bluefin]\nsections = [\"fedora\"]\n"
                "[utah]\npackages = []\n"
                "[unavailable]\npackages = [\"ghost\"]\n",
            )
            with self.assertRaisesRegex(ValueError, "ghost"):
                resolve(bluefin, policy)

    def test_rejects_missing_bluefin_section(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bluefin = self.write(root, "bluefin.toml", "[fedora]\npackages = [\"one\"]\n")
            policy = self.write(
                root,
                "policy.toml",
                BASE_POLICY
                + "[bluefin]\nsections = [\"missing\"]\n"
                "[utah]\npackages = []\n"
                "[unavailable]\npackages = []\n",
            )
            with self.assertRaisesRegex(ValueError, "no \\[missing\\]"):
                resolve(bluefin, policy)

    def test_rejects_mutable_base_image(self) -> None:
        with self.assertRaisesRegex(ValueError, "pinned by sha256"):
            base_image({"base": {"image": "quay.io/example/base:latest"}})


if __name__ == "__main__":
    unittest.main()
