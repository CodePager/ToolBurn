"""Offline parsers for local Codex/OpenClaw JSONL evidence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from toolburn.schema import connect


TOKEN_EVENT_TYPE = "token_count"
ROLLOUT_GLOB = "rollout-*.jsonl"


@dataclass(frozen=True)
class SourceSpec:
    label: str
    path: Path


@dataclass
class ParsedSession:
    session_id: str
    actor_id: str
    actor_type: str
    source: str
    path: Path
    workspace: str
    started_at: str
    ended_at: str
    label_confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


def scan_sources(db_path: Path, sources: Iterable[SourceSpec]) -> dict[str, int]:
    with connect(db_path) as conn:
        counts = {"files": 0, "sessions": 0, "token_events": 0, "invocations": 0}
        for source in sources:
            for path in iter_jsonl_paths(source.path):
                parsed = parse_session_file(path, source.label)
                if parsed is None:
                    continue
                upsert_session(conn, parsed)
                counts["files"] += 1
                counts["sessions"] += 1
                counts["token_events"] += insert_token_events(conn, parsed)
                counts["invocations"] += insert_invocations(conn, parsed)
        conn.commit()
    return counts


def iter_jsonl_paths(path: Path) -> Iterable[Path]:
    if path.is_file():
        if path.suffix == ".jsonl":
            yield path
        return
    if not path.exists():
        return
    yield from sorted(path.rglob(ROLLOUT_GLOB))


def parse_session_file(path: Path, source_label: str) -> ParsedSession | None:
    meta: dict[str, Any] = {}
    token_rows: list[dict[str, Any]] = []
    invocations: list[dict[str, Any]] = []
    evidence_text: list[str] = []
    pending_calls: dict[str, dict[str, Any]] = {}

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    for line_no, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = row.get("payload") or {}
        row_type = row.get("type")
        ts = row.get("timestamp") or payload.get("timestamp") or ""

        if row_type == "session_meta":
            meta.update(payload)
            continue

        if row_type == "event_msg" and payload.get("type") == TOKEN_EVENT_TYPE:
            token_rows.append({"row": row, "line_no": line_no})
            continue

        if row_type != "response_item" or not isinstance(payload, dict):
            continue

        text = compact_text(payload)
        if text:
            evidence_text.append(text[:2000])

        if payload.get("type") in {"function_call", "custom_tool_call"}:
            call_id = payload.get("call_id") or payload.get("id") or stable_id(
                path, "call", str(line_no)
            )
            command = command_from_call_payload(payload)
            if command:
                pending_calls[call_id] = {
                    "call_id": call_id,
                    "command": command,
                    "started_at": ts,
                    "line_no": line_no,
                    "cwd": meta.get("cwd") or "",
                }
            continue

        if payload.get("type") == "function_call_output":
            call_id = payload.get("call_id") or ""
            pending = pending_calls.pop(call_id, None)
            if pending:
                output = str(payload.get("output") or "")
                pending.update(
                    {
                        "ended_at": ts,
                        "output_bytes": len(output.encode("utf-8")),
                        "output_fingerprint": sha256_text(output),
                        "output_shape": output_shape(output),
                    }
                )
                invocations.append(pending)

    session_id = str(meta.get("id") or stable_id(path, "session"))
    actor_id, actor_type, confidence = infer_actor_id(
        source_label, path, meta, evidence_text
    )
    started_at = str(meta.get("timestamp") or first_timestamp(token_rows) or "")
    ended_at = last_timestamp(token_rows) or started_at
    parsed = ParsedSession(
        session_id=session_id,
        actor_id=actor_id,
        actor_type=actor_type,
        source=source_label,
        path=path,
        workspace=str(meta.get("cwd") or ""),
        started_at=started_at,
        ended_at=ended_at,
        label_confidence=confidence,
        metadata={
            "session_meta": scrub_meta(meta),
            "token_rows": token_rows,
            "invocations": invocations,
        },
    )
    return parsed if token_rows or invocations or meta else None


def upsert_session(conn, parsed: ParsedSession) -> None:
    conn.execute(
        """
        insert into actors(actor_id, actor_type, source, label_confidence, first_seen, last_seen, metadata_json)
        values(?, ?, ?, ?, ?, ?, ?)
        on conflict(actor_id) do update set
          first_seen = min(coalesce(first_seen, excluded.first_seen), excluded.first_seen),
          last_seen = max(coalesce(last_seen, excluded.last_seen), excluded.last_seen),
          label_confidence = max(label_confidence, excluded.label_confidence)
        """,
        (
            parsed.actor_id,
            parsed.actor_type,
            parsed.source,
            parsed.label_confidence,
            parsed.started_at,
            parsed.ended_at,
            json.dumps({"source_path": str(parsed.path)}, sort_keys=True),
        ),
    )
    conn.execute(
        """
        insert into sessions(session_id, actor_id, source, path, workspace, started_at, ended_at, metadata_json)
        values(?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id) do update set
          actor_id=excluded.actor_id,
          source=excluded.source,
          path=excluded.path,
          workspace=excluded.workspace,
          started_at=excluded.started_at,
          ended_at=excluded.ended_at,
          metadata_json=excluded.metadata_json
        """,
        (
            parsed.session_id,
            parsed.actor_id,
            parsed.source,
            str(parsed.path),
            parsed.workspace,
            parsed.started_at,
            parsed.ended_at,
            json.dumps(parsed.metadata["session_meta"], sort_keys=True),
        ),
    )


def insert_token_events(conn, parsed: ParsedSession) -> int:
    inserted = 0
    invocation_by_line = {
        int(invocation["line_no"]): stable_id(
            parsed.path, "invocation", str(invocation["line_no"])
        )
        for invocation in parsed.metadata["invocations"]
    }
    for item in parsed.metadata["token_rows"]:
        row = item["row"]
        payload = row.get("payload") or {}
        info = payload.get("info") or {}
        usage = info.get("last_token_usage") or {}
        event_id = stable_id(parsed.path, "token", str(item["line_no"]))
        invocation_id = nearest_invocation_id(invocation_by_line, int(item["line_no"]))
        conn.execute(
            """
            insert or replace into token_events(
              token_event_id, session_id, actor_id, invocation_id, ts, model,
              input_tokens, cached_input_tokens, output_tokens, raw_total_tokens, source_path
            )
            values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                parsed.session_id,
                parsed.actor_id,
                invocation_id,
                row.get("timestamp") or "",
                "",
                int(usage.get("input_tokens") or 0),
                int(usage.get("cached_input_tokens") or 0),
                int(usage.get("output_tokens") or 0),
                int(usage.get("total_tokens") or 0),
                str(parsed.path),
            ),
        )
        inserted += 1
    return inserted


def nearest_invocation_id(invocation_by_line: dict[int, str], token_line: int) -> str | None:
    previous = [line for line in invocation_by_line if line <= token_line]
    if not previous:
        return None
    return invocation_by_line[max(previous)]


def insert_invocations(conn, parsed: ParsedSession) -> int:
    inserted = 0
    for invocation in parsed.metadata["invocations"]:
        command = invocation["command"]
        tool_id = stable_id("tool", normalize_command(command))
        conn.execute(
            """
            insert or replace into tools(tool_id, normalized_command, executable, cwd, fingerprint, metadata_json)
            values(?, ?, ?, ?, ?, ?)
            """,
            (
                tool_id,
                normalize_command(command),
                executable(command),
                invocation.get("cwd") or parsed.workspace,
                stable_id("cmd", normalize_command(command)),
                "{}",
            ),
        )
        invocation_id = stable_id(parsed.path, "invocation", str(invocation["line_no"]))
        conn.execute(
            """
            insert or replace into invocations(
              invocation_id, session_id, actor_id, tool_id, started_at, ended_at,
              output_bytes, output_fingerprint, output_shape_json
            )
            values(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invocation_id,
                parsed.session_id,
                parsed.actor_id,
                tool_id,
                invocation.get("started_at") or "",
                invocation.get("ended_at") or "",
                int(invocation.get("output_bytes") or 0),
                invocation.get("output_fingerprint") or "",
                json.dumps(invocation.get("output_shape") or {}, sort_keys=True),
            ),
        )
        inserted += 1
    return inserted


def infer_actor_id(
    source_label: str, path: Path, meta: dict[str, Any], evidence_text: list[str]
) -> tuple[str, str, float]:
    haystack = "\n".join(evidence_text)
    session_id = str(meta.get("id") or stable_id(path, "session"))[:12]
    if "sessionKey" in haystack and ":direct:" in haystack:
        match = re.search(r"agent:[^:]+:[^:]+:direct:(\d+)", haystack)
        suffix = match.group(1) if match else "unknown"
        return f"background.openclaw.direct-session.{suffix}", "background", 0.78
    if "GOS watchdog 30m" in haystack or "run_watchdog_cycle.py" in haystack:
        return "background.openclaw.gos-watchdog-30m", "background", 0.8
    if "heartbeat_scan.py" in haystack or "spam_cleanup.py" in haystack:
        return "background.openclaw.heartbeat", "background", 0.75
    if "openclaw" in source_label.lower() or "/.openclaw/" in str(path):
        return f"unknown.openclaw-session.{session_id}", "unknown", 0.45
    workspace = slug(str(meta.get("cwd") or path.parent.name))
    if workspace:
        return f"unknown.human-like.codex-session.{workspace}", "unknown", 0.35
    return f"unknown.codex-session.{session_id}", "unknown", 0.2


def command_from_call_payload(payload: dict[str, Any]) -> str:
    arguments = payload.get("arguments")
    if isinstance(arguments, str):
        try:
            decoded = json.loads(arguments)
        except json.JSONDecodeError:
            decoded = {}
        if isinstance(decoded, dict):
            command = decoded.get("command") or decoded.get("cmd")
            if isinstance(command, str):
                return command.strip()
            return ""
        return arguments.strip()
    if isinstance(arguments, dict):
        command = arguments.get("command") or arguments.get("cmd")
        if isinstance(command, str):
            return command.strip()
    return ""


def compact_text(payload: dict[str, Any]) -> str:
    values: list[str] = []
    if isinstance(payload.get("content"), list):
        for part in payload["content"]:
            if isinstance(part, dict):
                text = part.get("text") or part.get("output_text")
                if isinstance(text, str):
                    values.append(text)
    for key in ("output", "arguments", "name"):
        value = payload.get(key)
        if isinstance(value, str):
            values.append(value)
    return "\n".join(values)


def first_timestamp(token_rows: list[dict[str, Any]]) -> str:
    if not token_rows:
        return ""
    return str(token_rows[0]["row"].get("timestamp") or "")


def last_timestamp(token_rows: list[dict[str, Any]]) -> str:
    if not token_rows:
        return ""
    return str(token_rows[-1]["row"].get("timestamp") or "")


def scrub_meta(meta: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "id",
        "timestamp",
        "cwd",
        "originator",
        "cli_version",
        "source",
        "model_provider",
    }
    return {key: meta.get(key) for key in sorted(allowed) if key in meta}


def output_shape(output: str) -> dict[str, Any]:
    stripped = output.strip()
    shape = {"bytes": len(output.encode("utf-8")), "lines": output.count("\n") + 1}
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            shape["format"] = "text"
        else:
            shape["format"] = "json"
            if isinstance(parsed, dict):
                shape["keys"] = sorted(str(key) for key in parsed.keys())[:20]
            elif isinstance(parsed, list):
                shape["items"] = len(parsed)
    else:
        shape["format"] = "text"
    return shape


def normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", command.strip())


def executable(command: str) -> str:
    normalized = normalize_command(command)
    return normalized.split(" ", 1)[0] if normalized else ""


def stable_id(*parts: object) -> str:
    joined = "\0".join(str(part) for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(text: str) -> str:
    stem = Path(text).name if "/" in text else text
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")[:48]
