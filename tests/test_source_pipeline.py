#!/usr/bin/env python3

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.source_pipeline import fetch_with_fallbacks


class SourcePipelineTests(unittest.TestCase):
    def test_uses_upstream_without_touching_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "source"
            with patch("tools.source_pipeline.fetch") as fetch:
                chosen = fetch_with_fallbacks(["https://upstream.example/source", "https://mirror.example/source"], destination)
            self.assertEqual(chosen, "https://upstream.example/source")
            fetch.assert_called_once_with("https://upstream.example/source", destination)

    def test_uses_fallback_only_after_upstream_transport_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "source"
            with patch(
                "tools.source_pipeline.fetch",
                side_effect=[RuntimeError("HTTP Error 418"), None],
            ) as fetch:
                chosen = fetch_with_fallbacks(["https://upstream.example/source", "https://mirror.example/source"], destination)
            self.assertEqual(chosen, "https://mirror.example/source")
            self.assertEqual(fetch.call_count, 2)

    def test_reports_every_failed_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "source"
            with patch("tools.source_pipeline.fetch", side_effect=RuntimeError("offline")):
                with self.assertRaisesRegex(RuntimeError, "upstream.example.*mirror.example"):
                    fetch_with_fallbacks(["https://upstream.example/source", "https://mirror.example/source"], destination)


if __name__ == "__main__":
    unittest.main()
