# Interface contract

Run `python -m importproof compare BEFORE AFTER --output NEWDIR`; optional `--policy policy.json`, `--keys id,code`, and `--ignore-order` set explicit rules. JSON input parsing options belong in `before` and `after` policy objects. CLI flags override their corresponding policy fields. Standard output is the complete report as one JSON object; progress and output-location messages use standard error. Exit codes: 0 equivalent; 2 findings or unknown; 1 invalid input, processing, or file-output failure. Argument syntax errors use argparse's exit 2. Reports use `report.json`, `report.html`, and `report.csv`. The output directory must not already exist, and its parent must exist.

Run `python -m importproof serve --port 8766`, then open `http://127.0.0.1:8766`. Port 0 chooses an available port. The startup message prints the actual address. Stop with Ctrl+C. Runtime assets are local and dependency free. Inputs, rules and results remain on the computer. Exports contain raw evidence and may contain private data.

Python interfaces:

- `reports.render_html(report: dict) -> str`
- `reports.render_csv(report: dict) -> str`
- `reports.write_reports(report: dict, output: str | Path) -> None`
- `cli.main(argv=None) -> int`
- `web.create_server(port: int = 0) -> HTTPServer`; caller runs `serve_forever()` and closes the server.

Both entry points call `worker.audit_bytes(before, before_name, after, after_name, options)`. HTML is inert and escapes all evidence. JSON preserves the full report. CSV JSON-encodes before/after evidence and prefixes dangerous scalar values with a single quote to inhibit spreadsheet formulas. CSV is a findings index; use JSON for the complete report policy and metadata.

HTTP routes:

- `GET /`, `/app.js`, `/style.css` serve allowlisted local assets.
- `GET /api/config` returns `token` and `max_file_bytes` after Host and optional Origin checks.
- `POST /api/compare` requires `Content-Type: application/json` and `X-ImportProof-Token`. Body: `{before:{name,data},after:{name,data},options:{}}`, where data is strict base64. Returns `{report,html,csv}` or a JSON `error` with an appropriate HTTP status.

The server binds IPv4 `127.0.0.1` only. Host must be the exact bound `127.0.0.1:PORT`; any supplied Origin must be the matching HTTP origin. Cross-site fetches are rejected. Duplicate Host/Origin/token/content-length headers are rejected. There is no CORS opt-in. The token is random per server run and never embedded in assets or logged. Uploaded names must be basenames, and uploads never name or open arbitrary server files.

The server processes one HTTP request at a time with a bounded backlog of four and a 10-second accepted-socket timeout. The shared worker imposes its own process deadline. JSON body limit is 15 MiB, each decoded input is at most 5 MiB, and generated responses are capped at 24 MiB. Oversized responses return an error rather than a partial success. This is a local review tool, not a public service or a complete operating-system sandbox.

Tests use generated synthetic CSV data and actual loopback HTTP and worker calls. Browser acceptance should additionally cover real file selection, filter changes, and all three downloads. No named spreadsheet application's conversion behavior is inferred from these controlled fixtures.
