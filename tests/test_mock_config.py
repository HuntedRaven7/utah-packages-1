#!/usr/bin/env python3

from pathlib import Path
import unittest

from tools.render_mock_config import render_mock_config

ROOT = Path(__file__).resolve().parent.parent


class MockConfigTests(unittest.TestCase):
    def test_mock_root_targets_hummingbird(self):
        text = render_mock_config("file:///work/prior/repository")
        self.assertIn("releasever=44", text)
        self.assertIn("public-hummingbird", text)
        self.assertLess(text.index("priority=10"), text.index("[fedora]"))
        self.assertIn("file:///work/prior/repository", text)
        self.assertIn("networking = False", text)

    def test_mock_root_without_prior_stage(self):
        text = render_mock_config()
        self.assertIn("releasever=44", text)
        self.assertIn("public-hummingbird", text)
        self.assertNotIn("work/prior", text)
        self.assertIn("networking = False", text)


if __name__ == "__main__":
    unittest.main()
