import json
import tempfile
import unittest
from pathlib import Path

from script_05_compute_unused import compute_and_export


class ComputeUnusedTests(unittest.TestCase):
    def test_refuses_incomplete_pagination_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()

            with self.assertRaisesRegex(RuntimeError, "pagination did not complete"):
                compute_and_export(
                    tmp,
                    str(run_dir),
                    all_accounts=[{"id": 1}],
                    mapping_rows=[],
                    associated_ids=set(),
                    disconnected_accounts=[],
                    diagnostics={"all_accounts": {"pagination_complete": False}},
                )

    def test_summary_includes_fetch_diagnostics_and_missing_associated_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            diagnostics = {"all_accounts": {"pagination_complete": True, "pages_fetched": 2}}

            summary = compute_and_export(
                tmp,
                str(run_dir),
                all_accounts=[{"id": 1}, {"id": 2}],
                mapping_rows=[],
                associated_ids={1, 99},
                disconnected_accounts=[{"id": 1}],
                diagnostics=diagnostics,
            )

            self.assertEqual(summary["associated_ids_missing_from_all_accounts_count"], 1)
            self.assertEqual(summary["fetch_diagnostics"], diagnostics)
            written_summary = json.loads((run_dir / "summary.json").read_text())
            self.assertEqual(written_summary["fetch_diagnostics"], diagnostics)


if __name__ == "__main__":
    unittest.main()
