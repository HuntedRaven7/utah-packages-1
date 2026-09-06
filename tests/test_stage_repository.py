#!/usr/bin/env python3

from pathlib import Path
import unittest

from tools.package_inventory import inventory
from tools.stage_repository import group_by_stage, KNOWN_EDGES

ROOT = Path(__file__).resolve().parent.parent


class StageRepositoryTests(unittest.TestCase):
    def test_group_by_stage_covers_all_stages(self):
        records = inventory(ROOT)
        grouped = group_by_stage(records)
        self.assertEqual(sorted(grouped.keys()), [0, 1, 2, 3, 4])
        total = sum(len(pkgs) for pkgs in grouped.values())
        self.assertEqual(total, len(records))

    def test_known_dependency_edges_respect_stage_ordering(self):
        records = {r.name: r for r in inventory(ROOT)}
        for upstream, downstream in KNOWN_EDGES:
            self.assertIn(upstream, records)
            self.assertIn(downstream, records)
            self.assertLess(
                records[upstream].stage,
                records[downstream].stage,
                f"{upstream} (stage {records[upstream].stage}) must precede {downstream} (stage {records[downstream].stage})"
            )


if __name__ == "__main__":
    unittest.main()
