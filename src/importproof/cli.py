"""Command line entry points sharing the bounded audit worker with the web UI."""
import argparse
import json
from pathlib import Path
import sys

from .models import MAX_FILE_BYTES
from .reports import write_reports


def _read(path, limit):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"File exceeds {limit} bytes: {Path(path).name}")
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="importproof", description="Review CSV, TSV and XLSX import fidelity locally.")
    commands = parser.add_subparsers(dest="command", required=True)
    compare = commands.add_parser("compare", help="Compare two files using explicit rules")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    compare.add_argument("--policy", type=Path, help="JSON object with comparison and input parsing options")
    compare.add_argument("--keys", help="Comma-separated exact column names or #N references; overrides policy keys")
    compare.add_argument("--ignore-order", action="store_true", default=None, help="Allow row and column order differences")
    compare.add_argument("--output", type=Path, help="New directory for report.json, report.html and report.csv")
    server = commands.add_parser("serve", help="Start the local browser interface at 127.0.0.1")
    server.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            from .web import create_server
            with create_server(args.port) as httpd:
                print(f"ImportProof is running at http://127.0.0.1:{httpd.server_port}", flush=True)
                print("Keep this terminal open. Press Ctrl+C to stop.", flush=True)
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    pass
            return 0
        options = {}
        if args.policy:
            options = json.loads(_read(args.policy, 128 * 1024).decode("utf-8-sig"))
            if not isinstance(options, dict):
                raise ValueError("Policy must be a JSON object")
        if args.keys is not None:
            options["keys"] = [key.strip() for key in args.keys.split(",")]
            if any(not key for key in options["keys"]):
                raise ValueError("--keys requires nonempty column names")
        if args.ignore_order is not None:
            options["ignore_order"] = args.ignore_order
        if args.output and args.output.exists():
            raise ValueError("Output directory already exists; choose a new directory")
        from .worker import audit_bytes
        report = audit_bytes(_read(args.before, MAX_FILE_BYTES), args.before.name,
                             _read(args.after, MAX_FILE_BYTES), args.after.name, options)
        if args.output:
            write_reports(report, args.output)
        print(json.dumps(report, ensure_ascii=True, allow_nan=False))
        if args.output:
            print(f"Reports: {args.output.resolve()}", file=sys.stderr)
        return 0 if report["verdict"] == "EQUIVALENT" else 2
    except (OSError, ValueError) as error:
        print(f"ImportProof error: {error}", file=sys.stderr)
        return 1
