#!/usr/bin/env python3
"""Validate analyst evidence, calculate supplied-data windows, or export annotations."""

import argparse
import json
from pathlib import Path
import sys

from forensics_core import benchmark_windows, event_window, export_events, validate_evidence


def read_json(path):
    def invalid(value):
        raise ValueError(f"Non-finite JSON number: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", help="Check evidence consistency, not source truth")
    check.add_argument("--input", required=True)
    window = sub.add_parser("price-window", help="Use daily session closes supplied as JSON")
    window.add_argument("--prices", required=True)
    window.add_argument("--benchmark", action="append", default=[], metavar="[SYMBOL=]JSON",
                        help="Daily benchmark JSON; repeat to compare a broad market and industry ETF")
    window.add_argument("--event-date", required=True)
    window.add_argument("--timing", choices=["before-open", "after-close", "during-session", "unknown"], default="unknown")
    export = sub.add_parser("export-events")
    export.add_argument("--input", required=True)
    export.add_argument("--prices", required=True)
    for command in (check, window, export):
        command.add_argument("--output", help="Create a new JSON file; existing paths are never overwritten")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            errors = validate_evidence(read_json(args.input))
            result = {"valid": not errors, "errors": errors, "scope": "structure and attribution eligibility only; facts require source review"}
            code = 1 if errors else 0
        elif args.command == "price-window":
            benchmarks = {}
            paths = {}
            for spec in args.benchmark:
                symbol, path = spec.split("=", 1) if "=" in spec else (Path(spec).stem.upper(), spec)
                if not symbol or not path:
                    raise ValueError("Benchmark syntax is [SYMBOL=]JSON")
                if symbol in benchmarks:
                    raise ValueError(f"Duplicate benchmark symbol: {symbol}")
                benchmarks[symbol] = read_json(path)
                paths[symbol] = str(Path(path))
            prices = read_json(args.prices)
            if len(benchmarks) > 1:
                windows = benchmark_windows(prices, args.event_date, args.timing, benchmarks)
                result = {"event_date": args.event_date, "timing": args.timing,
                          "benchmark_comparisons": [{"symbol": symbol, "data_path": paths[symbol],
                                                      "reaction": reaction}
                                                     for symbol, reaction in windows.items()]}
            else:
                result = event_window(prices, args.event_date, args.timing,
                                      next(iter(benchmarks.values())) if benchmarks else None)
            code = 0
        else:
            result = export_events(read_json(args.input), read_json(args.prices))
            code = 0
        output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            with Path(args.output).open("x", encoding="utf-8") as handle:
                handle.write(output)
        else:
            print(output, end="")
        return code
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
