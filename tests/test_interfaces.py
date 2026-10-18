"""Observable CLI and export contracts; inputs are synthetic public fixtures."""
import csv
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


def sample_report():
    return {
        "schema_version": "1", "version": "0.1.0", "verdict": "CONFIRMED_LOSS",
        "inputs": {"before": {"name": "<script>alert(1)</script>"}, "after": {}},
        "policy": {}, "assumptions": ["Positional alignment"],
        "summary": {"CONFIRMED_LOSS": 1, "SUSPECTED_CONVERSION": 0, "EQUIVALENT": 0, "UNKNOWN": 0},
        "findings": [{"verdict": "CONFIRMED_LOSS", "code": "=BAD()", "message": "<img src=x onerror=alert(1)>",
                      "table": "+table", "before": {"row": 2, "column": 1, "cell": {"raw": "=1+1", "kind": "text"}},
                      "after": {"row": 2, "column": 1, "cell": {"raw": "2", "kind": "text"}}}],
        "truncated": False,
    }


class ReportTests(unittest.TestCase):
    def setUp(self):
        try:
            self.reports = importlib.import_module("importproof.reports")
        except ModuleNotFoundError:
            self.fail("The report export module has not been implemented")

    def test_html_escapes_untrusted_metadata_and_evidence(self):
        result = self.reports.render_html(sample_report())
        self.assertNotIn("<script>", result)
        self.assertNotIn("<img src=x", result)
        self.assertIn("&lt;script&gt;", result)
        self.assertIn("=1+1", result)
        self.assertIn("Positional alignment", result)

    def test_csv_guards_scalar_formulas_and_preserves_raw_evidence(self):
        rows = list(csv.DictReader(io.StringIO(self.reports.render_csv(sample_report()))))
        self.assertEqual(rows[0]["code"], "'=BAD()")
        self.assertEqual(rows[0]["table"], "'+table")
        self.assertEqual(json.loads(rows[0]["before"])["cell"]["raw"], "=1+1")

    def test_new_directory_exports_three_formats_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "reports"
            self.reports.write_reports(sample_report(), output)
            self.assertEqual(set(p.name for p in output.iterdir()), {"report.json", "report.html", "report.csv"})
            self.assertEqual(json.loads((output / "report.json").read_text(encoding="utf-8")), sample_report())
            with self.assertRaises((ValueError, FileExistsError)):
                self.reports.write_reports(sample_report(), output)
            self.assertEqual(json.loads((output / "report.json").read_text(encoding="utf-8")), sample_report())


class CliTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run([sys.executable, "-m", "importproof", *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=45)

    def test_actual_worker_cli_equivalent_and_loss_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before, after = root / "before.csv", root / "after.csv"
            before.write_bytes(b"id,value\n1,001\n")
            after.write_bytes(before.read_bytes())
            equal = self.invoke("compare", before, after, "--output", root / "equal")
            self.assertEqual(equal.returncode, 0, equal.stderr)
            self.assertEqual(json.loads(equal.stdout)["verdict"], "EQUIVALENT")
            self.assertEqual(json.loads((root / "equal/report.json").read_text(encoding="utf-8"))["verdict"], "EQUIVALENT")
            after.write_bytes(b"id,value\n1,1\n")
            loss = self.invoke("compare", before, after, "--keys", "id", "--output", root / "loss")
            self.assertEqual(loss.returncode, 2, loss.stderr)
            self.assertEqual(json.loads(loss.stdout)["verdict"], "CONFIRMED_LOSS")

    def test_invalid_policy_and_existing_output_fail_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.csv"
            source.write_bytes(b"id\n1\n")
            policy = root / "policy.json"
            policy.write_text('{"unknown_policy":true}', encoding="utf-8")
            invalid = self.invoke("compare", source, source, "--policy", policy)
            self.assertEqual(invalid.returncode, 1, invalid.stderr)
            self.assertIn("ImportProof error:", invalid.stderr)
            existing = root / "existing"
            existing.mkdir()
            marker = existing / "keep.txt"
            marker.write_text("keep", encoding="utf-8")
            collision = self.invoke("compare", source, source, "--output", existing)
            self.assertEqual(collision.returncode, 1, collision.stderr)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_argparse_syntax_uses_exit_two(self):
        result = self.invoke("compare")
        self.assertEqual(result.returncode, 2, result.stderr)


if __name__ == "__main__":
    unittest.main()
