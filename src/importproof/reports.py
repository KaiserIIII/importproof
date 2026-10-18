"""Local, inert evidence exports. JSON retains the original report unchanged."""
import csv
import html
import io
import json
from pathlib import Path


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def _escape(value):
    return html.escape(str(value), quote=True)


def _safe_csv(value):
    text = "" if value is None else str(value)
    # Quotes in CSV alone do not prevent spreadsheet formula execution.
    if text.startswith(("\t", "\r", "\n")) or text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def render_csv(report: dict) -> str:
    """Render findings; JSON evidence preserves raw values without cell formulas."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["verdict", "code", "message", "table", "before", "after", "details"])
    writer.writeheader()
    for finding in report.get("findings", []):
        row = {key: finding.get(key, "") for key in ("verdict", "code", "message", "table")}
        row["before"] = _json(finding.get("before"))
        row["after"] = _json(finding.get("after"))
        row["details"] = _json({key: value for key, value in finding.items() if key not in row})
        writer.writerow({key: _safe_csv(value) for key, value in row.items()})
    return output.getvalue()


def render_html(report: dict) -> str:
    """Render a standalone report with escaped evidence and no active content."""
    summary = "".join(f'<li><strong>{_escape(key.replace("_", " "))}</strong> {_escape(value)}</li>'
                      for key, value in report.get("summary", {}).items())
    findings = []
    for index, finding in enumerate(report.get("findings", []), 1):
        findings.append(
            f'<article><h3>{index}. {_escape(finding.get("verdict", "UNKNOWN"))} · {_escape(finding.get("code", ""))}</h3>'
            f'<p>{_escape(finding.get("message", ""))}</p><p>Table: {_escape(finding.get("table", ""))}</p>'
            '<div class="evidence"><section><h4>Before</h4><pre>' + _escape(_json(finding.get("before"))) + '</pre></section>'
            '<section><h4>After</h4><pre>' + _escape(_json(finding.get("after"))) + '</pre></section></div>'
            '<details><summary>Complete finding</summary><pre>' + _escape(_json(finding)) + '</pre></details></article>')
    return '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + \
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;">' + \
        '<title>ImportProof evidence report</title><style>' + \
        'body{font:16px/1.55 system-ui,sans-serif;color:#1b2939;background:#f4f7fb;margin:0}main{max-width:1100px;margin:auto;padding:36px 24px}h1{letter-spacing:-.04em}article,details.panel{background:white;border:1px solid #ced9e6;border-radius:12px;padding:20px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5fa;padding:14px;border-radius:8px;font-size:13px}.evidence{display:grid;grid-template-columns:1fr 1fr;gap:16px}li{margin:6px 0}summary{cursor:pointer;font-weight:600}@media(max-width:700px){.evidence{grid-template-columns:1fr}}' + \
        '</style></head><body><main><p>IMPORTPROOF · LOCAL EVIDENCE REPORT</p><h1>' + _escape(report.get("verdict", "UNKNOWN")) + \
        '</h1><p>Observed differences under the recorded rules. Findings do not establish software causality or business intent.</p><ul>' + summary + \
        '</ul><p>Truncated: ' + _escape(report.get("truncated", False)) + '</p>' + \
        '<details class="panel" open><summary>Inputs, policy and assumptions</summary><pre>' + \
        _escape(_json({key: value for key, value in report.items() if key != "findings"})) + '</pre></details><h2>Findings</h2>' + \
        ("".join(findings) or '<p>No findings. Review the recorded policy and assumptions above.</p>') + '</main></body></html>'


def write_reports(report: dict, output: str | Path) -> None:
    """Write three reports into a newly created directory; never overwrite."""
    contents = {"report.json": _json(report) + "\n", "report.html": render_html(report), "report.csv": render_csv(report)}
    directory = Path(output)
    directory.mkdir(parents=False, exist_ok=False)
    for name, content in contents.items():
        with (directory / name).open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
