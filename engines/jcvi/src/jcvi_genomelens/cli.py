"""Standalone CLI entrypoint for the JCVI engine."""

# region import
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# endregion


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jcvi_genomelens.engine_runtime import run_manifest
from jcvi_genomelens.probe import build_probe_payload


def build_parser() -> argparse.ArgumentParser:
    """Build the engine CLI parser."""

    parser = argparse.ArgumentParser(prog="jcvi-genomelens", description="GenomeLens JCVI engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe", help="print engine probe payload")
    probe.add_argument("--json", action="store_true", help="print JSON output")
    probe.set_defaults(func=run_probe)

    run = subparsers.add_parser("run", help="run a manifest")
    run.add_argument("--manifest", required=True)
    run.add_argument("--outdir", required=True)
    run.set_defaults(func=run_engine)
    return parser


def run_probe(args: argparse.Namespace) -> int:
    """Print the engine probe payload."""

    payload = build_probe_payload()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{payload['engine_name']} {payload['engine_version']} status={payload['status']}")
    return 0


def run_engine(args: argparse.Namespace) -> int:
    """Run a manifest and return the process exit code."""

    summary = run_manifest(args.manifest, args.outdir)
    payload = json.loads(summary.read_text(encoding="utf-8"))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") == "ok" else 7


def main(argv: list[str] | None = None) -> int:
    """Run the engine CLI entrypoint."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
