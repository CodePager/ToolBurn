"""Toolburn command line interface."""

from __future__ import annotations

import argparse
from pathlib import Path

from toolburn import __version__
from toolburn.schema import initialize_database, table_names


PLANNED_COMMANDS = ("scan", "du", "top", "tree", "explain", "export")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="toolburn",
        description="Local-first token burn profiler.",
    )
    parser.add_argument("--version", action="version", version=f"toolburn {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    schema_parser = subparsers.add_parser("schema", help="initialize a Toolburn SQLite DB")
    schema_parser.add_argument("--db", required=True, type=Path, help="SQLite DB path")

    for command in PLANNED_COMMANDS:
        planned = subparsers.add_parser(command, help=f"planned Phase 1 command: {command}")
        planned.set_defaults(planned_command=command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "schema":
        initialize_database(args.db)
        print(f"initialized {args.db}")
        print("\n".join(table_names(args.db)))
        return 0

    if getattr(args, "planned_command", None):
        print(f"toolburn {args.planned_command} is planned for Phase 1 implementation")
        return 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

