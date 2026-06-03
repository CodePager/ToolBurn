"""Toolburn command line interface."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import gettempdir

from toolburn import __version__
from toolburn.report import export_json, format_explain, format_table, du_report, explain_report, top_report
from toolburn.scan import SourceSpec, scan_sources
from toolburn.schema import initialize_database, table_names


REPORT_GROUPS = ("actor", "session", "source", "tool")
ACTOR_TYPES = ("human", "background", "unknown")
DEFAULT_CODEX_ROOT = Path("/root/.codex/sessions")
DEFAULT_OPENCLAW_ROOT = Path("/root/.openclaw/agents/main/agent/codex-home/sessions")
DEFAULT_COPILOT_ROOT = Path("/root/.copilot/session-state")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="toolburn",
        description="Local-first token burn profiler.",
    )
    parser.add_argument("--version", action="version", version=f"toolburn {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    schema_parser = subparsers.add_parser("schema", help="initialize a Toolburn SQLite DB")
    schema_parser.add_argument("--db", required=True, type=Path, help="SQLite DB path")

    scan_parser = subparsers.add_parser("scan", help="scan local JSONL evidence into SQLite")
    scan_parser.add_argument("--db", required=True, type=Path, help="SQLite DB path")
    scan_parser.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help="source label and file/directory path; may be repeated",
    )
    scan_parser.add_argument("--codex", type=Path, help="Codex sessions directory or JSONL file")
    scan_parser.add_argument("--openclaw", type=Path, help="OpenClaw sessions directory or JSONL file")
    scan_parser.add_argument("--copilot", type=Path, help="GitHub Copilot session-state directory or JSONL file")

    recent_parser = subparsers.add_parser(
        "recent", help="scan local defaults and show recent token burn"
    )
    recent_parser.add_argument("--hours", type=float, default=24.0, help="lookback window")
    recent_parser.add_argument("--limit", type=int, default=10)
    recent_parser.add_argument("--db", type=Path, help="SQLite DB path")
    recent_parser.add_argument("--no-scan", action="store_true", help="reuse the DB")
    recent_parser.add_argument("--actor-type", choices=ACTOR_TYPES, help="only show one actor type")
    recent_parser.add_argument("--codex", type=Path, default=DEFAULT_CODEX_ROOT)
    recent_parser.add_argument("--openclaw", type=Path, default=DEFAULT_OPENCLAW_ROOT)
    recent_parser.add_argument("--copilot", type=Path, default=DEFAULT_COPILOT_ROOT)

    subparsers.add_parser("sources", help="show supported and planned evidence sources")

    for command in ("du", "top"):
        report_parser = subparsers.add_parser(command, help=f"show token usage by {command}")
        report_parser.add_argument("--db", required=True, type=Path, help="SQLite DB path")
        report_parser.add_argument("--by", choices=REPORT_GROUPS, default="actor")
        report_parser.add_argument("--limit", type=int, default=20)
        report_parser.add_argument("--since", help="inclusive ISO timestamp lower bound")
        report_parser.add_argument("--actor-type", choices=ACTOR_TYPES, help="only show one actor type")

    tree_parser = subparsers.add_parser("tree", help="show compact actor drilldown")
    tree_parser.add_argument("--db", required=True, type=Path, help="SQLite DB path")
    tree_parser.add_argument("target", help="actor_id or session_id")

    explain_parser = subparsers.add_parser("explain", help="explain an actor or session")
    explain_parser.add_argument("--db", required=True, type=Path, help="SQLite DB path")
    explain_parser.add_argument("target", help="actor_id or session_id")
    explain_parser.add_argument("--for-agent", action="store_true")

    export_parser = subparsers.add_parser("export", help="export compact JSON for an agent")
    export_parser.add_argument("--db", required=True, type=Path, help="SQLite DB path")
    export_parser.add_argument("--target", help="optional actor_id or session_id")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "schema":
        initialize_database(args.db)
        print(f"initialized {args.db}")
        print("\n".join(table_names(args.db)))
        return 0

    if args.command == "scan":
        sources = parse_sources(args)
        if not sources:
            parser.error("scan requires at least one --source, --codex, --openclaw, or --copilot path")
        counts = scan_sources(args.db, sources)
        print(
            "scanned {files} files, {sessions} sessions, {token_events} token events, "
            "{invocations} invocations".format(**counts)
        )
        return 0

    if args.command == "recent":
        db_path = args.db or default_recent_db_path()
        since = hours_ago_iso(args.hours)
        sources = existing_default_sources(args)
        if not args.no_scan:
            if not sources:
                parser.error("no default Codex/OpenClaw/Copilot session roots found")
            counts = scan_sources(db_path, sources)
            print(
                "scanned {files} files, {sessions} sessions, {token_events} token events, "
                "{invocations} invocations".format(**counts)
            )
        print(f"since {since}")
        if args.actor_type:
            print(f"actor_type {args.actor_type}")
        print("")
        print("Top actors")
        print(
            format_table(
                top_report(
                    db_path,
                    group_by="actor",
                    limit=args.limit,
                    since=since,
                    actor_type=args.actor_type,
                )
            )
        )
        print("")
        print("Top tools")
        print(
            format_table(
                top_report(
                    db_path,
                    group_by="tool",
                    limit=args.limit,
                    since=since,
                    actor_type=args.actor_type,
                )
            )
        )
        return 0

    if args.command == "sources":
        print(format_sources())
        return 0

    if args.command == "du":
        print(
            format_table(
                du_report(
                    args.db,
                    group_by=args.by,
                    limit=args.limit,
                    since=args.since,
                    actor_type=args.actor_type,
                )
            )
        )
        return 0

    if args.command == "top":
        print(
            format_table(
                top_report(
                    args.db,
                    group_by=args.by,
                    limit=args.limit,
                    since=args.since,
                    actor_type=args.actor_type,
                )
            )
        )
        return 0

    if args.command == "tree":
        print(format_explain(explain_report(args.db, args.target), for_agent=False))
        return 0

    if args.command == "explain":
        print(format_explain(explain_report(args.db, args.target), for_agent=args.for_agent))
        return 0

    if args.command == "export":
        print(export_json(args.db, args.target))
        return 0

    parser.print_help()
    return 0


def parse_sources(args: argparse.Namespace) -> list[SourceSpec]:
    sources: list[SourceSpec] = []
    if args.codex:
        sources.append(SourceSpec("codex", args.codex))
    if args.openclaw:
        sources.append(SourceSpec("openclaw", args.openclaw))
    if getattr(args, "copilot", None):
        sources.append(SourceSpec("github-copilot", args.copilot))
    for item in args.source:
        if "=" not in item:
            raise SystemExit(f"--source must use LABEL=PATH: {item}")
        label, raw_path = item.split("=", 1)
        sources.append(SourceSpec(label.strip(), Path(raw_path)))
    return sources


def existing_default_sources(args: argparse.Namespace) -> list[SourceSpec]:
    sources = []
    if args.codex and args.codex.exists():
        sources.append(SourceSpec("codex", args.codex))
    if args.openclaw and args.openclaw.exists():
        sources.append(SourceSpec("openclaw", args.openclaw))
    if args.copilot and args.copilot.exists():
        sources.append(SourceSpec("github-copilot", args.copilot))
    return sources


def hours_ago_iso(hours: float) -> str:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    return since.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def default_recent_db_path() -> Path:
    return Path(gettempdir()) / "toolburn-recent.sqlite"


def format_sources() -> str:
    rows = [
        ("codex", "supported", str(DEFAULT_CODEX_ROOT), "Codex rollout JSONL token_count rows"),
        ("openclaw", "supported", str(DEFAULT_OPENCLAW_ROOT), "OpenClaw-owned Codex rollout JSONL"),
        (
            "github-copilot",
            "experimental",
            str(DEFAULT_COPILOT_ROOT),
            "Copilot CLI session-state events.jsonl; shutdown/model usage is cumulative",
        ),
        (
            "claude-code",
            "untested",
            "~/.claude",
            "settings and CLAUDE.md locations are documented; transcript parsing waits for a confirmed session sample",
        ),
    ]
    width = max(len(row[0]) for row in rows)
    return "\n".join(
        f"{name:<{width}}  {status:<12}  {path}  {note}" for name, status, path, note in rows
    )


if __name__ == "__main__":
    raise SystemExit(main())
