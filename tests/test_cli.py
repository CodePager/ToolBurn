from __future__ import annotations

import contextlib
import json
import io
import tempfile
import unittest
from pathlib import Path

from toolburn.cli import main


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def fixture_rows() -> list[dict]:
    return [
        {
            "timestamp": "2026-06-01T22:54:15.000Z",
            "type": "session_meta",
            "payload": {
                "id": "session-1",
                "timestamp": "2026-06-01T22:54:15.000Z",
                "cwd": "/root/.openclaw/workspace",
                "originator": "openclaw",
                "source": "vscode",
            },
        },
        {
            "timestamp": "2026-06-01T22:54:20.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "call_id": "call-1",
                "name": "shell_command",
                "arguments": json.dumps(
                    {
                        "command": (
                            "python3 state/ops-harness/scripts/run_watchdog_cycle.py "
                            "--dispatch-mode real"
                        )
                    }
                ),
            },
        },
        {
            "timestamp": "2026-06-01T22:54:22.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": "call-1",
                "output": json.dumps(
                    {
                        "name": "GOS watchdog 30m",
                        "sessionKey": "agent:main:chat:direct:0000000000",
                        "ok": True,
                    }
                ),
            },
        },
        {
            "timestamp": "2026-06-01T22:54:26.000Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {"total_tokens": 300},
                    "last_token_usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 80,
                        "output_tokens": 5,
                        "total_tokens": 105,
                    },
                },
            },
        },
        {
            "timestamp": "2026-06-01T22:54:29.000Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {"total_tokens": 1000},
                    "last_token_usage": {
                        "input_tokens": 200,
                        "cached_input_tokens": 180,
                        "output_tokens": 10,
                        "total_tokens": 210,
                    },
                },
            },
        },
    ]


def copilot_fixture_rows() -> list[dict]:
    return [
        {
            "type": "session.start",
            "data": {
                "sessionId": "copilot-session-1",
                "producer": "copilot-agent",
                "copilotVersion": "1.0.31",
                "startTime": "2026-06-01T22:54:15.000Z",
                "context": {"cwd": "/srv/pager/repos/toolburn"},
            },
            "id": "start-1",
            "timestamp": "2026-06-01T22:54:15.000Z",
        },
        {
            "type": "assistant.usage",
            "data": {
                "model": "claude-sonnet-test",
                "inputTokens": 120,
                "outputTokens": 30,
                "cacheReadTokens": 100,
                "cacheWriteTokens": 5,
                "reasoningTokens": 10,
            },
            "id": "usage-1",
            "timestamp": "2026-06-01T22:54:20.000Z",
        },
        {
            "type": "session.shutdown",
            "data": {
                "modelMetrics": {
                    "claude-opus-test": {
                        "requests": {"count": 2, "cost": 1},
                        "usage": {
                            "inputTokens": 200,
                            "outputTokens": 40,
                            "cacheReadTokens": 160,
                            "cacheWriteTokens": 0,
                            "reasoningTokens": 0,
                        },
                    }
                }
            },
            "id": "shutdown-1",
            "timestamp": "2026-06-01T22:55:20.000Z",
        },
    ]


class CliTests(unittest.TestCase):
    def test_help_returns_zero(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main([]), 0)
        self.assertIn("Local-first token burn profiler", stdout.getvalue())

    def test_scan_and_du_use_last_token_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence = root / "rollout-2026-06-01T22-54-15-test.jsonl"
            db_path = root / "toolburn.sqlite"
            write_jsonl(evidence, fixture_rows())

            scan_out = io.StringIO()
            with contextlib.redirect_stdout(scan_out):
                self.assertEqual(
                    main(["scan", "--db", str(db_path), "--source", f"openclaw={evidence}"]),
                    0,
                )
            self.assertIn("2 token events", scan_out.getvalue())

            du_out = io.StringIO()
            with contextlib.redirect_stdout(du_out):
                self.assertEqual(main(["du", "--db", str(db_path), "--by", "actor"]), 0)
            output = du_out.getvalue()
            self.assertIn("315 raw", output)
            self.assertIn("background.openclaw.direct-session.0000000000", output)

            tool_out = io.StringIO()
            with contextlib.redirect_stdout(tool_out):
                self.assertEqual(main(["top", "--db", str(db_path), "--by", "tool"]), 0)
            self.assertIn("run_watchdog_cycle.py", tool_out.getvalue())

    def test_explain_for_agent_exports_compact_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence = root / "rollout-2026-06-01T22-54-15-test.jsonl"
            db_path = root / "toolburn.sqlite"
            write_jsonl(evidence, fixture_rows())
            main(["scan", "--db", str(db_path), "--openclaw", str(evidence)])

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "explain",
                            "--db",
                            str(db_path),
                            "background.openclaw.direct-session.0000000000",
                            "--for-agent",
                        ]
                    ),
                    0,
                )
            output = stdout.getvalue()
            self.assertIn("Toolburn finding", output)
            self.assertIn("context_leak", output)
            self.assertIn("Agent handoff JSON:", output)

    def test_recent_scans_defaults_and_prints_actors_and_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sessions = root / "sessions"
            evidence = sessions / "rollout-2026-06-01T22-54-15-test.jsonl"
            db_path = root / "toolburn.sqlite"
            write_jsonl(evidence, fixture_rows())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(
                    main(
                        [
                            "recent",
                            "--hours",
                            "999999",
                            "--db",
                            str(db_path),
                            "--codex",
                            str(root / "missing-codex"),
                            "--openclaw",
                            str(sessions),
                        ]
                    ),
                    0,
                )
            output = stdout.getvalue()
            self.assertIn("Top actors", output)
            self.assertIn("Top tools", output)
            self.assertIn("run_watchdog_cycle.py", output)

    def test_scan_supports_github_copilot_events_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence = root / "session-state" / "copilot-session-1" / "events.jsonl"
            db_path = root / "toolburn.sqlite"
            write_jsonl(evidence, copilot_fixture_rows())

            scan_out = io.StringIO()
            with contextlib.redirect_stdout(scan_out):
                self.assertEqual(main(["scan", "--db", str(db_path), "--copilot", str(root)]), 0)
            self.assertIn("2 token events", scan_out.getvalue())

            du_out = io.StringIO()
            with contextlib.redirect_stdout(du_out):
                self.assertEqual(main(["du", "--db", str(db_path), "--by", "actor"]), 0)
            output = du_out.getvalue()
            self.assertIn("400 raw", output)
            self.assertIn("260 cached", output)
            self.assertIn("unknown.github-copilot.toolburn", output)

    def test_sources_command_lists_support_status(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["sources"]), 0)
        output = stdout.getvalue()
        self.assertIn("github-copilot", output)
        self.assertIn("experimental", output)
        self.assertIn("claude-code", output)
        self.assertIn("untested", output)


if __name__ == "__main__":
    unittest.main()
