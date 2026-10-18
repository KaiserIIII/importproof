"""Deterministic evidence-bound comparison. No fuzzy identity or application attribution."""
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import re
import unicodedata

from .models import MAX_FINDINGS, AuditError

VERDICTS = ("CONFIRMED_LOSS", "SUSPECTED_CONVERSION", "EQUIVALENT", "UNKNOWN")
DEFAULTS = {"keys": [], "ignore_order": False, "text_columns": [], "numeric_columns": [],
            "date_columns": [], "ignore_columns": [], "date_formats": ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"],
            "trim_whitespace": False, "unicode_normalization": "none", "null_tokens": [],
            "column_map": {}, "before": {}, "after": {}, "before_sheet": None, "after_sheet": None}


def validate_policy(options=None):
    if options is None:
        options = {}
    if not isinstance(options, dict) or set(options) - set(DEFAULTS):
        raise AuditError("Unknown policy fields or policy is not an object")
    p = {**DEFAULTS, **options}
    for name in ("keys", "text_columns", "numeric_columns", "date_columns", "ignore_columns", "date_formats", "null_tokens"):
        if not isinstance(p[name], list) or len(p[name]) > 256 or any(not isinstance(v, str) or len(v) > 256 for v in p[name]):
            raise AuditError(name + " must be a bounded list of strings")
        if len(p[name]) != len(set(p[name])):
            raise AuditError(name + " has duplicate entries")
    for name in ("ignore_order", "trim_whitespace"):
        if type(p[name]) is not bool:
            raise AuditError(name + " must be boolean")
    if p["unicode_normalization"] not in ("none", "NFC", "NFKC"):
        raise AuditError("unicode_normalization must be none, NFC or NFKC")
    for name in ("before", "after"):
        if not isinstance(p[name], dict):
            raise AuditError(name + " input policy must be an object")
    if not isinstance(p["column_map"], dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in p["column_map"].items()):
        raise AuditError("column_map must map exact column references")
    if len(set(p["column_map"].values())) != len(p["column_map"]):
        raise AuditError("column_map targets must be unique")
    for name in ("before_sheet", "after_sheet"):
        if p[name] is not None and (not isinstance(p[name], str) or not p[name] or len(p[name]) > 256):
            raise AuditError(name + " must be a sheet name")
    return p


def _headers(table):
    return [c["raw"] if c["raw"] is not None else "" for c in table["headers"]]


def _resolve(ref, names):
    if re.fullmatch(r"#[1-9]\d*", ref):
        index = int(ref[1:]) - 1
        if index < len(names):
            return index
    elif names.count(ref) == 1:
        return names.index(ref)
    raise AuditError(f"Column {ref!r} missing or ambiguous; use #1-based position for duplicate names")


def _decimal(value):
    if not isinstance(value, str) or len(value) > 2048 or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,4})?", value):
        raise ValueError("not a bounded finite decimal")
    n = Decimal(value)
    if not n.is_finite():
        raise ValueError("nonfinite decimal")
    return n


def _date(cell, p):
    raw = cell["raw"]
    if not isinstance(raw, str):
        raise ValueError("not a date")
    candidates = set()
    if cell["kind"] == "date":
        try:
            candidates.add(datetime.fromisoformat(raw).isoformat())
        except ValueError:
            pass
    for fmt in p["date_formats"]:
        try:
            candidates.add(datetime.strptime(raw, fmt).isoformat())
        except (ValueError, OverflowError):
            pass
    if len(candidates) != 1:
        raise ValueError("date has no unique interpretation under selected formats")
    return candidates.pop()


def _raw_key(cell):
    return cell["kind"], cell["raw"]


def _semantic(cell, mode, p):
    if cell["kind"] in ("formula", "error", "missing"):
        raise ValueError("formula, error or absent cell needs review")
    value = cell["raw"]
    if value in p["null_tokens"] or value is None and "" in p["null_tokens"]:
        return ("null", None)
    if value is None:
        return (cell["kind"], None)
    if p["trim_whitespace"]:
        value = value.strip()
    if p["unicode_normalization"] != "none":
        value = unicodedata.normalize(p["unicode_normalization"], value)
    if mode == "number":
        return ("number", _decimal(value))
    if mode == "date":
        return ("date", _date({**cell, "raw": value}, p))
    if mode == "text" and cell["kind"] not in ("text", "empty"):
        return ("not-text-" + cell["kind"], value)
    return (cell["kind"], value)


def compare_documents(before, after, options=None):
    p = validate_policy(options)
    report = {"schema_version": 1, "version": "0.1.0", "inputs": {
        "before": {k: v for k, v in before.items() if k != "tables"},
        "after": {k: v for k, v in after.items() if k != "tables"}}, "policy": p,
        "assumptions": ["Input origins and before/after roles are caller supplied; hashes identify bytes only.",
                        "Observed difference does not establish intent or which application caused it.",
                        "Header is the first record; all default sheets compared. No fuzzy identity matching."],
        "findings": [], "truncated": False}

    def emit(verdict, code, message, table=None, b=None, a=None):
        if len(report["findings"]) >= MAX_FINDINGS:
            report["truncated"] = True
            return
        report["findings"].append({"verdict": verdict, "code": code, "message": message, "table": table, "before": b, "after": a})

    def evidence(row, index, table, names):
        cell = row["cells"][index] if index < len(row["cells"]) else {"kind": "missing", "raw": None, "coordinate": None}
        return {"row": row["number"], "column": names[index] if index < len(names) else f"#{index+1}", "column_index": index + 1,
                "sheet": table, "source": row.get("source"), "cell": cell}

    bt = {t["name"]: t for t in before["tables"]}; at = {t["name"]: t for t in after["tables"]}
    if p["before_sheet"] or p["after_sheet"]:
        if not p["before_sheet"] or not p["after_sheet"] or p["before_sheet"] not in bt or p["after_sheet"] not in at:
            raise AuditError("Select existing before_sheet and after_sheet together")
        pairs = [(bt[p["before_sheet"]], at[p["after_sheet"]])]
        report["assumptions"].append("Only explicitly selected sheet pair is in scope; all other sheets excluded.")
    elif len(bt) == len(at) == 1 and (before["format"] != "xlsx" or after["format"] != "xlsx"):
        pairs = [(next(iter(bt.values())), next(iter(at.values())))]
    else:
        pairs = [(bt[n], at[n]) for n in bt if n in at]
        for name in sorted(bt.keys() - at.keys()):
            emit("CONFIRMED_LOSS", "SHEET_LOST", "Before sheet absent from after document", name)
        for name in sorted(at.keys() - bt.keys()):
            emit("CONFIRMED_LOSS", "SHEET_ADDED", "After sheet absent from before document", name)

    for btable, atable in pairs:
        table = btable["name"]
        bn, an = _headers(btable), _headers(atable)
        for t, side in ((btable, "before"), (atable, "after")):
            for issue in t.get("issues", []):
                emit("UNKNOWN", issue["code"], side + ": " + issue["message"], table, issue if side == "before" else None, issue if side == "after" else None)
        if any(n == "" or bn.count(n) > 1 for n in bn) or any(n == "" or an.count(n) > 1 for n in an):
            emit("UNKNOWN", "AMBIGUOUS_HEADER", "Duplicate/empty headers retained by position; no unique name identity", table)
        ignored = {_resolve(x, bn) for x in p["ignore_columns"]}
        modes = {}
        for key, mode in (("text_columns", "text"), ("numeric_columns", "number"), ("date_columns", "date")):
            for ref in p[key]:
                i = _resolve(ref, bn)
                if i in modes or i in ignored:
                    raise AuditError("Conflicting semantic/text/ignored column policies")
                modes[i] = mode
        colmap = {_resolve(k, bn): _resolve(v, an) for k, v in p["column_map"].items()}
        if len(colmap) != len(p["column_map"]):
            raise AuditError("Multiple column_map references name the same source column")
        for i, name in enumerate(bn):
            if i in colmap:
                continue
            if bn.count(name) == an.count(name) == 1:
                colmap[i] = an.index(name)
            elif bn == an:
                colmap[i] = i
        if len(set(colmap.values())) != len(colmap):
            raise AuditError("Two before columns resolve to one after column")
        for i, name in enumerate(bn):
            if i not in colmap and i not in ignored:
                emit("CONFIRMED_LOSS", "COLUMN_LOST", "Before column has no exact or caller-mapped after column", table, {"column": name, "column_index": i+1})
        for j, name in enumerate(an):
            if j not in colmap.values():
                emit("CONFIRMED_LOSS", "COLUMN_ADDED", "New column; any rename cause remains unproven", table, None, {"column": name, "column_index": j+1})
        ordered_targets = [colmap[i] for i in sorted(colmap)]
        if ordered_targets != sorted(ordered_targets):
            emit("EQUIVALENT" if p["ignore_order"] else "CONFIRMED_LOSS", "COLUMN_ORDER_CHANGED", "Exact columns were reordered", table)
        for i, j in colmap.items():
            bh, ah = btable['headers'][i], atable['headers'][j]
            if i not in ignored and bh['kind'] in ('number','date') and ah['kind']==bh['kind'] and bh.get('format') != ah.get('format'):
                emit('UNKNOWN', 'HEADER_DISPLAY_FORMAT_CHANGED', 'Header display format changed; name alignment does not certify rendered header fidelity', table,
                     {'row': 1, 'column': bn[i], 'column_index': i+1, 'cell': bh},
                     {'row': 1, 'column': an[j], 'column_index': j+1, 'cell': ah})
            if bh['kind'] != ah['kind'] and i not in ignored:
                emit('CONFIRMED_LOSS', 'HEADER_TYPE_CHANGED', 'Header storage type changed; column name alignment alone does not establish fidelity', table,
                     {'row': 1, 'column': bn[i], 'column_index': i+1, 'cell': bh},
                     {'row': 1, 'column': an[j], 'column_index': j+1, 'cell': ah})
            if bn[i] != an[j]:
                emit("EQUIVALENT", "COLUMN_RENAMED_BY_POLICY", "Caller explicitly mapped column names", table, {"column": bn[i]}, {"column": an[j]})
        bkeys = [_resolve(ref, bn) for ref in p["keys"]]
        if len(set(bkeys)) != len(bkeys) or any(i in ignored for i in bkeys):
            raise AuditError("Key column is ignored or repeated by an alias")
        if any(i not in colmap for i in bkeys):
            emit("UNKNOWN", "KEY_COLUMN_LOST", "Key column absent after import; cell identity cannot be established", table)
            continue
        akeys = [colmap[i] for i in bkeys]
        selected = [(i, j) for i, j in colmap.items() if i not in ignored]

        def rowkey(row, indices):
            cells = [row["cells"][i] if i < len(row["cells"]) else {"kind": "missing", "raw": None} for i in indices]
            if any(c["kind"] in ("blank", "empty", "missing", "formula", "error") or c["raw"] in p["null_tokens"] for c in cells):
                return None
            return tuple(_raw_key(c) for c in cells)

        def fingerprint(row):
            return tuple(_raw_key(c) for c in row["cells"])

        for rows, side in ((btable["rows"], "before"), (atable["rows"], "after")):
            seen = Counter(fingerprint(row) for row in rows)
            for row in rows:
                if seen[fingerprint(row)] > 1:
                    emit("UNKNOWN", "DUPLICATE_ROW", side + " contains repeated exact records; multiplicity retained", table,
                         {"row": row["number"]} if side == "before" else None, {"row": row["number"]} if side == "after" else None)
                    seen[fingerprint(row)] = 0
        matches = []
        if bkeys:
            bg, ag = defaultdict(list), defaultdict(list)
            for row in btable["rows"]:
                bg[rowkey(row, bkeys)].append(row)
            for row in atable["rows"]:
                ag[rowkey(row, akeys)].append(row)
            matched_positions = []
            # insertion order avoids randomized set order across runtimes.
            for key in dict.fromkeys([*bg, *ag]):
                br, ar = bg[key], ag[key]
                if key is None or len(br) > 1 or len(ar) > 1:
                    emit("UNKNOWN", "AMBIGUOUS_KEY", "Missing/duplicate key group is not arbitrarily paired", table,
                         {"rows": [r["number"] for r in br]}, {"rows": [r["number"] for r in ar]})
                    continue
                if not br:
                    emit("CONFIRMED_LOSS", "ROW_ADDED", "New exact key under caller identity assumption", table, None, {"row": ar[0]["number"], "cells": ar[0]["cells"]})
                elif not ar:
                    emit("CONFIRMED_LOSS", "ROW_LOST", "Exact key absent under caller identity assumption", table, {"row": br[0]["number"], "cells": br[0]["cells"]})
                else:
                    matches.append((br[0], ar[0])); matched_positions.append(ar[0]["number"])
            if matched_positions != sorted(matched_positions):
                emit("EQUIVALENT" if p["ignore_order"] else "CONFIRMED_LOSS", "ROW_ORDER_CHANGED", "Stable-key rows were reordered", table)
        elif p["ignore_order"]:
            report["assumptions"].append("No keys + ignore_order: exact multiset matching only; changed rows have UNKNOWN identity.")
            def signature(row, side):
                values = []
                for i, j in selected:
                    index = i if side == "before" else j
                    c = row["cells"][index] if index < len(row["cells"]) else {"kind": "missing", "raw": None}
                    try:
                        values.append(_semantic(c, modes.get(i), p))
                    except ValueError:
                        values.append(_raw_key(c))
                return tuple(values)
            bg, ag = defaultdict(list), defaultdict(list)
            for row in btable["rows"]:
                bg[signature(row, "before")].append(row)
            for row in atable["rows"]:
                ag[signature(row, "after")].append(row)
            for key in dict.fromkeys([*bg, *ag]):
                br, ar = bg[key], ag[key]
                for b, a in zip(br, ar):
                    matches.append((b, a))
                if len(br) != len(ar):
                    emit("UNKNOWN", "UNMATCHED_ROWS", "Unmatched multiset records; changed versus lost/added identity cannot be resolved", table,
                         {"rows": [r["number"] for r in br[len(ar):]]}, {"rows": [r["number"] for r in ar[len(br):]]})
            if len(btable["rows"]) != len(atable["rows"]):
                emit("CONFIRMED_LOSS", "ROW_COUNT_CHANGED", "Observed record multiplicity changed", table, {"count": len(btable["rows"])}, {"count": len(atable["rows"])})
            elif [signature(r, "before") for r in btable["rows"]] != [signature(r, "after") for r in atable["rows"]] and len(matches) == len(btable["rows"]):
                emit("EQUIVALENT", "ROW_ORDER_CHANGED", "Multiset equality with ordering explicitly ignored", table)
        else:
            report["assumptions"].append("No keys: records compared by position; cell findings assume corresponding record positions.")
            matches = list(zip(btable["rows"], atable["rows"]))
            for side, rows, start in (("before", btable["rows"], len(atable["rows"])), ("after", atable["rows"], len(btable["rows"]))):
                for row in rows[start:]:
                    emit("CONFIRMED_LOSS", "ROW_LOST" if side == "before" else "ROW_ADDED", "Unpaired positional record", table,
                         {"row": row["number"], "cells": row["cells"]} if side == "before" else None, {"row": row["number"], "cells": row["cells"]} if side == "after" else None)

        for brow, arow in matches:
            for i, j in selected:
                b, a = evidence(brow, i, table, bn), evidence(arow, j, atable["name"], an)
                bc, ac = b["cell"], a["cell"]
                if any(c["kind"] == "text" and isinstance(c["raw"], str) and c["raw"].lstrip().startswith(("=", "@", "+", "-")) and not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", c["raw"]) for c in (bc, ac)):
                    emit("UNKNOWN", "FORMULA_LIKE_TEXT", "Text could be interpreted as a formula by a later spreadsheet importer; never executed here", table, b, a)
                if bc["kind"] in ("formula", "error", "missing") or ac["kind"] in ("formula", "error", "missing"):
                    emit("UNKNOWN", "FORMULA_OR_UNAVAILABLE_CELL", "Formula/error/absent cell is never evaluated or certified equal", table, b, a)
                    continue
                mode = modes.get(i)
                try:
                    equivalent = _semantic(bc, mode, p) == _semantic(ac, mode, p)
                except (ValueError, InvalidOperation, OverflowError):
                    emit("UNKNOWN", "SEMANTIC_INTERPRETATION", "Values have no reliable interpretation under requested semantic rule", table, b, a)
                    continue
                raw_same = _raw_key(bc) == _raw_key(ac)
                date_format_changed = bc["kind"] == ac["kind"] == "date" and bc.get("format") != ac.get("format")
                number_format_changed = bc['kind'] == ac['kind'] == 'number' and bc.get('format') != ac.get('format')
                if number_format_changed and mode != 'number':
                    emit('UNKNOWN', 'NUMBER_DISPLAY_FORMAT_CHANGED', 'Stored numbers have different display formats; rendered value is not certified', table, b, a)
                elif number_format_changed:
                    emit('EQUIVALENT', 'NUMBER_FORMAT_IGNORED_BY_POLICY', 'Numeric semantic rule excludes display formatting; original formats retained', table, b, a)
                if equivalent and (not date_format_changed or mode == "date"):
                    if not raw_same or date_format_changed:
                        emit("EQUIVALENT", "RULE_EQUIVALENT", "Representations equivalent under the recorded caller rule", table, b, a)
                    continue
                x, y = bc["raw"], ac["raw"]
                code = "VALUE_CHANGED"
                if bc["kind"] in ("blank", "empty") or ac["kind"] in ("blank", "empty"):
                    code = "EMPTY_NULL_CHANGE"
                elif isinstance(x, str) and isinstance(y, str):
                    if x.strip() == y.strip() and x != y:
                        code = "WHITESPACE_CHANGED"
                    elif unicodedata.normalize("NFC", x) == unicodedata.normalize("NFC", y) or any(ord(c) > 127 for c in x + y):
                        code = "UNICODE_TEXT_CHANGED"
                    try:
                        dx, dy = _decimal(x), _decimal(y)
                        code = "DECIMAL_REPRESENTATION_CHANGED" if dx == dy else "NUMERIC_VALUE_CHANGED"
                        if len(re.sub(r"\D", "", x)) > 15 and dx != dy:
                            code = "LONG_NUMBER_PRECISION_CHANGE"
                        if re.fullmatch(r"[+-]?0\d+", x) and dx == dy and not re.fullmatch(r"[+-]?0\d+", y):
                            emit("SUSPECTED_CONVERSION", "LEADING_ZERO_REMOVED", "Pattern consistent with numeric conversion; cause unproven", table, b, a)
                        if bool(re.search(r"[eE]", x)) != bool(re.search(r"[eE]", y)):
                            emit("SUSPECTED_CONVERSION", "SCIENTIFIC_NOTATION_CHANGE", "Scientific notation representation changed; cause unproven", table, b, a)
                    except (ValueError, InvalidOperation):
                        pass
                if bc["kind"] != ac["kind"] and code == "VALUE_CHANGED":
                    code = "TYPE_CHANGED"
                if "date" in (bc["kind"], ac["kind"]) or date_format_changed:
                    code = "DATE_FORMAT_CHANGED" if date_format_changed else "DATE_OR_TYPE_CHANGED"
                    if bc["kind"] == "text" and ac["kind"] == "date":
                        emit("SUSPECTED_CONVERSION", "TEXT_TO_DATE", "Text became stored date; application and intent unproven", table, b, a)
                elif isinstance(x, str) and isinstance(y, str) and re.fullmatch(r"\d{1,4}[-/]\d{1,2}(?:[-/]\d{1,4})?", x) and re.fullmatch(r"\d{1,4}[-/]\d{1,2}(?:[-/]\d{1,4})?", y):
                    emit("SUSPECTED_CONVERSION", "POSSIBLE_DATE_CONVERSION", "Changed date-shaped text without a confirmed date interpretation", table, b, a)
                emit("CONFIRMED_LOSS", code, "Observed representation/type/value changed under selected rules; no application attribution", table, b, a)

    summary = {v: sum(f["verdict"] == v for f in report["findings"]) for v in VERDICTS}
    report["summary"] = summary
    report["verdict"] = "UNKNOWN" if report["truncated"] or summary["UNKNOWN"] else "CONFIRMED_LOSS" if summary["CONFIRMED_LOSS"] else "SUSPECTED_CONVERSION" if summary["SUSPECTED_CONVERSION"] else "EQUIVALENT"
    if not report["findings"]:
        report["assumptions"].append("No disallowed differences observed within supported data and explicit scope.")
    return report
