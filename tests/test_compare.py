"""Literal oracles for actual import loss and ambiguity; no production-helper oracles."""
import unittest
from importproof.compare import compare_documents


def document(rows, headers=("id", "value"), name="data", kinds=None):
    def cell(raw, index, row, kind=None):
        return {"raw": raw, "kind": kind or ("blank" if raw is None else "empty" if raw == "" else "text"), "coordinate": f"{row}:{index}"}
    return {"format": "csv", "sha256": "0" * 64, "bytes": 1, "metadata": {}, "tables": [{"name": name,
            "headers": [cell(value, i, 1) for i, value in enumerate(headers, 1)],
            "rows": [{"number": i, "source": {"line_start": i, "line_end": i}, "cells": [cell(value, j, i, (kinds or {}).get((i, j))) for j, value in enumerate(row, 1)]} for i, row in enumerate(rows, 2)], "issues": []}]}


def run(before, after, policy=None):
    return compare_documents(document(before), document(after), policy or {"keys": ["id"]})


class ComparisonTests(unittest.TestCase):
    def codes(self, report):
        return {item["code"] for item in report["findings"]}

    def test_leading_zero_is_observed_loss_but_cause_only_suspected(self):
        r = run([["a", "00123"]], [["a", "123"]])
        self.assertEqual(r["verdict"], "CONFIRMED_LOSS")
        self.assertIn("LEADING_ZERO_REMOVED", self.codes(r))
        self.assertEqual(next(f for f in r["findings"] if f["code"] == "LEADING_ZERO_REMOVED")["verdict"], "SUSPECTED_CONVERSION")

    def test_decimal_semantics_explicitly_allows_representation(self):
        self.assertEqual(run([["a", "1.00"]], [["a", "1"]], {"keys": ["id"], "numeric_columns": ["value"]})["verdict"], "EQUIVALENT")

    def test_long_numbers_compare_exactly_not_as_float(self):
        r = run([["a", "12345678901234567"]], [["a", "12345678901234568"]], {"keys": ["id"], "numeric_columns": ["value"]})
        self.assertEqual(r["verdict"], "CONFIRMED_LOSS")
        self.assertIn("LONG_NUMBER_PRECISION_CHANGE", self.codes(r))

    def test_scientific_conversion_flag_does_not_name_software(self):
        r = run([["a", "123000"]], [["a", "1.23E5"]])
        self.assertIn("SCIENTIFIC_NOTATION_CHANGE", self.codes(r))
        self.assertFalse(any("Excel" in f["message"] for f in r["findings"]))

    def test_semantic_numeric_invalid_is_unknown(self):
        r = run([["a", "1"]], [["a", "oops"]], {"keys": ["id"], "numeric_columns": ["value"]})
        self.assertEqual(r["verdict"], "UNKNOWN")

    def test_whitespace_default_and_explicit_ignore(self):
        self.assertEqual(run([["a", " x "]], [["a", "x"]])["verdict"], "CONFIRMED_LOSS")
        self.assertEqual(run([["a", " x "]], [["a", "x"]], {"keys": ["id"], "trim_whitespace": True})["verdict"], "EQUIVALENT")

    def test_unicode_normalization_is_explicit(self):
        self.assertEqual(run([["a", "é"]], [["a", "e\u0301"]])["verdict"], "CONFIRMED_LOSS")
        self.assertEqual(run([["a", "é"]], [["a", "e\u0301"]], {"keys": ["id"], "unicode_normalization": "NFC"})["verdict"], "EQUIVALENT")

    def test_blank_versus_empty_is_preserved(self):
        self.assertIn("EMPTY_NULL_CHANGE", self.codes(run([["a", None]], [["a", ""]])))

    def test_null_tokens_only_equate_when_declared(self):
        self.assertEqual(run([["a", "NA"]], [["a", "NULL"]], {"keys": ["id"], "null_tokens": ["NA", "NULL"]})["verdict"], "EQUIVALENT")

    def test_duplicate_keys_never_arbitrarily_paired(self):
        r = run([["a", "1"], ["a", "2"]], [["a", "1"], ["a", "9"]])
        self.assertEqual(r["verdict"], "UNKNOWN")
        self.assertIn("AMBIGUOUS_KEY", self.codes(r))
        self.assertNotIn("VALUE_CHANGED", self.codes(r))

    def test_missing_key_is_unknown(self):
        self.assertEqual(run([[None, "x"]], [[None, "x"]])["verdict"], "UNKNOWN")

    def test_keyed_lost_added_and_duplicate_row(self):
        r = run([["a", "1"], ["b", "2"]], [["a", "1"], ["c", "3"], ["c", "3"]])
        self.assertIn("ROW_LOST", self.codes(r))
        self.assertIn("DUPLICATE_ROW", self.codes(r))

    def test_composite_key_is_exact(self):
        r = run([["a", "1"], ["a", "2"]], [["a", "2"], ["a", "1"]], {"keys": ["id", "value"], "ignore_order": True})
        self.assertEqual(r["verdict"], "EQUIVALENT")

    def test_order_is_not_silently_ignored(self):
        a = [["a", "1"], ["b", "2"]]
        self.assertIn("ROW_ORDER_CHANGED", self.codes(run(a, a[::-1])))
        self.assertEqual(run(a, a[::-1], {"keys": ["id"], "ignore_order": True})["verdict"], "EQUIVALENT")

    def test_no_key_multiset_does_not_invent_matches(self):
        r = run([["a", "1"]], [["a", "2"]], {"ignore_order": True})
        self.assertEqual(r["verdict"], "UNKNOWN")

    def test_text_column_forbids_type_coercion(self):
        b = document([["a", "12"]]); a = document([["a", "12"]], kinds={(2, 2): "number"})
        self.assertEqual(compare_documents(b, a, {"keys": ["id"], "text_columns": ["value"]})["verdict"], "CONFIRMED_LOSS")

    def test_formula_is_not_equal_even_to_identical_formula(self):
        d = document([["a", "=1+1"]], kinds={(2, 2): "formula"})
        self.assertEqual(compare_documents(d, d, {})["verdict"], "UNKNOWN")

    def test_formula_like_csv_text_warns_without_executing(self):
        self.assertEqual(run([["a", '=HYPERLINK("https://example.invalid")']], [["a", '=HYPERLINK("https://example.invalid")']])["verdict"], "UNKNOWN")

    def test_lost_key_column_keeps_loss_and_alignment_unknown(self):
        b = document([["a", "x"]]); a = document([["x"]], headers=("value",))
        r = compare_documents(b, a, {"keys": ["id"]})
        self.assertEqual(r["verdict"], "UNKNOWN")
        self.assertIn("COLUMN_LOST", self.codes(r))

    def test_ambiguous_or_duplicate_policy_targets_rejected(self):
        for p in ({"keys": ["id", "#1"]}, {"column_map": {"id": "#1", "#1": "value"}}):
            with self.subTest(p=p), self.assertRaises(ValueError):
                compare_documents(document([["a", "x"]]), document([["a", "x"]]), p)

    def test_date_semantics_explicit_formats(self):
        r = run([["a", "2026-10-18"]], [["a", "18/10/2026"]], {"keys": ["id"], "date_columns": ["value"], "date_formats": ["%Y-%m-%d", "%d/%m/%Y"]})
        self.assertEqual(r["verdict"], "EQUIVALENT")

    def test_ambiguous_date_never_guessed(self):
        r = run([["a", "01/02/2026"]], [["a", "02/01/2026"]], {"keys": ["id"], "date_columns": ["value"], "date_formats": ["%d/%m/%Y", "%m/%d/%Y"]})
        self.assertEqual(r["verdict"], "UNKNOWN")

    def test_column_rename_requires_mapping(self):
        b = document([["a", "x"]]); a = document([["a", "x"]], headers=("id", "renamed"))
        self.assertEqual(compare_documents(b, a, {"keys": ["id"]})["verdict"], "CONFIRMED_LOSS")
        self.assertEqual(compare_documents(b, a, {"keys": ["id"], "column_map": {"value": "renamed"}})["verdict"], "EQUIVALENT")

    def test_missing_sheet_is_loss(self):
        b = document([["a", "x"]], name="one"); a = document([["a", "x"]], name="two")
        b["format"] = a["format"] = "xlsx"
        self.assertIn("SHEET_LOST", self.codes(compare_documents(b, a, {})))

    def test_duplicate_headers_surface_unknown(self):
        d = document([["a", "x"]], headers=("same", "same"))
        self.assertEqual(compare_documents(d, d, {})["verdict"], "UNKNOWN")

    def test_invalid_or_conflicting_policy_rejected(self):
        for policy in ({"typo": True}, {"numeric_columns": ["value"], "text_columns": ["value"]}, {"keys": "id"}, {"ignore_order": "false"}):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                run([["a", "1"]], [["a", "1"]], policy)

    def test_report_has_raw_evidence_and_input_hash(self):
        r = run([["a", "001"]], [["a", "1"]])
        self.assertEqual(r["inputs"]["before"]["sha256"], "0" * 64)
        self.assertTrue(any(f.get("before", {}).get("cell", {}).get("raw") == "001" for f in r["findings"] if f.get("before")))

    def test_ignoring_column_is_transparent(self):
        r = run([["a", "1"]], [["a", "2"]], {"keys": ["id"], "ignore_columns": ["value"]})
        self.assertEqual(r["verdict"], "EQUIVALENT")
        self.assertEqual(r["policy"]["ignore_columns"], ["value"])

    def test_findings_cap_never_false_equal(self):
        a = [[str(i), "a"] for i in range(2100)]; b = [[str(i), "b"] for i in range(2100)]
        r = run(a, b)
        self.assertTrue(r["truncated"])
        self.assertEqual(r["verdict"], "UNKNOWN")

    def test_header_storage_type_change_is_not_false_equality(self):
        b = document([["a", "x"]], headers=("123", "value"))
        a = document([["a", "x"]], headers=("123", "value"))
        a['tables'][0]['headers'][0]['kind'] = 'number'
        self.assertEqual(compare_documents(b, a, {})['verdict'], 'CONFIRMED_LOSS')

    def test_number_format_change_retains_uncertainty(self):
        b = document([["a", "123"]], kinds={(2,2):'number'})
        a = document([["a", "123"]], kinds={(2,2):'number'})
        b['tables'][0]['rows'][0]['cells'][1]['format'] = '00000'
        a['tables'][0]['rows'][0]['cells'][1]['format'] = 'General'
        self.assertEqual(compare_documents(b, a, {})['verdict'], 'UNKNOWN')

    def test_number_header_format_is_not_silently_ignored(self):
        b = document([["a", "x"]], headers=("123", "value"))
        a = document([["a", "x"]], headers=("123", "value"))
        for d in (b,a): d['tables'][0]['headers'][0]['kind']='number'
        b['tables'][0]['headers'][0]['format']='00000'
        a['tables'][0]['headers'][0]['format']='General'
        self.assertEqual(compare_documents(b,a,{})['verdict'],'UNKNOWN')


if __name__ == "__main__":
    unittest.main()
