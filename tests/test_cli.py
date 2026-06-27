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


def codex_fixture_rows() -> list[dict]:
    rows = fixture_rows()
    rows[0]["payload"] = {
        "id": "codex-session-1",
        "timestamp": "2026-06-01T22:54:15.000Z",
        "cwd": "/srv/pager",
        "originator": "codex",
        "source": "vscode",
    }
    rows[1]["payload"]["arguments"] = json.dumps({"command": "git status --short"})
    rows[2]["payload"]["output"] = "clean"
    return rows


def openclaw_cron_fixture_rows() -> list[dict]:
    rows = fixture_rows()
    rows[0]["payload"]["id"] = "cron-session-1"
    rows[1]["payload"]["arguments"] = json.dumps({"command": "tool_search exec command"})
    rows[2]["payload"]["output"] = "no tools found"
    rows.insert(
        1,
        {
            "timestamp": "2026-06-01T22:54:16.000Z",
            "type": "event_msg",
            "payload": {
                "type": "user_message",
                "message": (
                    "[cron:b2d1fd93-38c9-4c4f-bf58-926db57cf5d0 "
                    "voice-models daily maintain] Run the daily maintain cycle."
                ),
            },
        },
    )
    return rows


def openclaw_dream_fixture_rows() -> list[dict]:
    rows = fixture_rows()
    rows[0]["payload"]["id"] = "dream-session-1"
    rows[1]["payload"]["arguments"] = json.dumps({"command": "write"})
    rows[2]["payload"]["output"] = "done"
    rows.insert(
        1,
        {
            "timestamp": "2026-06-01T22:54:16.000Z",
            "type": "event_msg",
            "payload": {
                "type": "user_message",
                "message": "Write a dream diary entry from these memory fragments.",
            },
        },
    )
    return rows


def cached_validate_attribution_rows() -> list[dict]:
    return [
        {
            "timestamp": "2026-06-01T22:54:15.000Z",
            "type": "session_meta",
            "payload": {
                "id": "cached-validate-session",
                "timestamp": "2026-06-01T22:54:15.000Z",
                "cwd": "/srv/pager/repos/toolburn",
                "originator": "codex",
            },
        },
        {
            "timestamp": "2026-06-01T22:54:20.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "call_id": "call-validate",
                "name": "shell_command",
                "arguments": json.dumps({"command": "./scripts/validate.sh"}),
            },
        },
        {
            "timestamp": "2026-06-01T22:54:21.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": "call-validate",
                "output": "validation passed",
            },
        },
        {
            "timestamp": "2026-06-01T22:54:24.000Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 1000,
                        "cached_input_tokens": 990,
                        "output_tokens": 5,
                        "total_tokens": 1005,
                    },
                },
            },
        },
        {
            "timestamp": "2026-06-01T22:55:20.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "call_id": "call-heavy",
                "name": "shell_command",
                "arguments": json.dumps({"command": "python3 expensive_context.py"}),
            },
        },
        {
            "timestamp": "2026-06-01T22:55:21.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": "call-heavy",
                "output": "large fresh result",
            },
        },
        {
            "timestamp": "2026-06-01T22:55:24.000Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 200,
                        "cached_input_tokens": 10,
                        "output_tokens": 10,
                        "total_tokens": 210,
                    },
                },
            },
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
            self.assertIn("Top tool-contexts", output)
            self.assertIn("uncached", output)
            self.assertIn("run_watchdog_cycle.py", output)

    def test_tool_report_orders_by_uncached_context_not_cached_raw_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence = root / "rollout-2026-06-01T22-54-15-test.jsonl"
            db_path = root / "toolburn.sqlite"
            write_jsonl(evidence, cached_validate_attribution_rows())

            main(["scan", "--db", str(db_path), "--codex", str(evidence)])

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["top", "--db", str(db_path), "--by", "tool"]), 0)
            output = stdout.getvalue()
            self.assertIn("uncached", output)
            self.assertLess(
                output.index("python3 expensive_context.py"),
                output.index("./scripts/validate.sh"),
            )

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
            self.assertIn("human.github-copilot.workspace.toolburn", output)

    def test_sources_command_lists_support_status(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["sources"]), 0)
        output = stdout.getvalue()
        self.assertIn("github-copilot", output)
        self.assertIn("experimental", output)
        self.assertIn("claude-code", output)
        self.assertIn("untested", output)

    def test_codex_workspace_sessions_are_labeled_human(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence = root / "rollout-2026-06-01T22-54-15-test.jsonl"
            db_path = root / "toolburn.sqlite"
            write_jsonl(evidence, codex_fixture_rows())

            main(["scan", "--db", str(db_path), "--codex", str(evidence)])

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["du", "--db", str(db_path), "--by", "actor"]), 0)
            self.assertIn("human.codex.workspace.pager", stdout.getvalue())

    def test_openclaw_cron_and_dream_diary_sessions_are_labeled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "toolburn.sqlite"
            cron_evidence = root / "rollout-2026-06-01T22-54-15-cron.jsonl"
            dream_evidence = root / "rollout-2026-06-01T22-54-15-dream.jsonl"
            write_jsonl(cron_evidence, openclaw_cron_fixture_rows())
            write_jsonl(dream_evidence, openclaw_dream_fixture_rows())

            main(["scan", "--db", str(db_path), "--openclaw", str(root)])

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["du", "--db", str(db_path), "--by", "actor"]), 0)
            output = stdout.getvalue()
            self.assertIn("background.openclaw.cron.voice-models-daily-maintain", output)
            self.assertIn("background.openclaw.dream-diary", output)

    def test_reports_filter_by_actor_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "toolburn.sqlite"
            codex_evidence = root / "codex" / "rollout-2026-06-01T22-54-15-codex.jsonl"
            openclaw_evidence = root / "openclaw" / "rollout-2026-06-01T22-54-15-openclaw.jsonl"
            write_jsonl(codex_evidence, codex_fixture_rows())
            write_jsonl(openclaw_evidence, fixture_rows())

            main(
                [
                    "scan",
                    "--db",
                    str(db_path),
                    "--codex",
                    str(codex_evidence),
                    "--openclaw",
                    str(openclaw_evidence),
                ]
            )

            human_out = io.StringIO()
            with contextlib.redirect_stdout(human_out):
                self.assertEqual(
                    main(["top", "--db", str(db_path), "--by", "actor", "--actor-type", "human"]),
                    0,
                )
            self.assertIn("human.codex.workspace.pager", human_out.getvalue())
            self.assertNotIn("background.openclaw", human_out.getvalue())

            background_out = io.StringIO()
            with contextlib.redirect_stdout(background_out):
                self.assertEqual(
                    main(
                        [
                            "top",
                            "--db",
                            str(db_path),
                            "--by",
                            "actor",
                            "--actor-type",
                            "background",
                        ]
                    ),
                    0,
                )
            self.assertIn("background.openclaw.direct-session.0000000000", background_out.getvalue())
            self.assertNotIn("human.codex.workspace.pager", background_out.getvalue())


if __name__ == "__main__":
    unittest.main()
