#!/usr/bin/env python3
"""Collect bounded Claude Code and Codex session evidence for one local date."""

from __future__ import annotations

import argparse
from collections import deque
from datetime import date, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


LOCAL_ZONE = datetime.now().astimezone().tzinfo


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_ZONE)
    return parsed.astimezone(LOCAL_ZONE)


def flatten_text(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []

    texts: list[str] = []
    for block in value:
        if isinstance(block, str):
            texts.append(block)
            continue
        if not isinstance(block, dict):
            continue
        for key in ("text", "input_text", "output_text"):
            text = block.get(key)
            if isinstance(text, str):
                texts.append(text)
                break
    return texts


def message_from_line(data: dict[str, Any], agent: str) -> tuple[str, str] | None:
    if agent == "Claude Code":
        role = data.get("type")
        message = data.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
    else:
        if data.get("type") != "response_item":
            return None
        payload = data.get("payload", {})
        if not isinstance(payload, dict):
            return None
        role = payload.get("role")
        content = payload.get("content")

    if role not in {"user", "assistant"}:
        return None
    text = "\n".join(part.strip() for part in flatten_text(content) if part.strip())
    return (role, text) if text else None


def clip(text: str, limit: int) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def collect_session(path: Path, agent: str, limit: int) -> dict[str, Any] | None:
    users: list[str] = []
    assistants: deque[str] = deque(maxlen=2)
    timestamps: list[datetime] = []
    cwd = ""

    try:
        lines = path.open(encoding="utf-8", errors="replace")
        for line in lines:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            timestamp = parse_timestamp(data.get("timestamp"))
            if timestamp:
                timestamps.append(timestamp)

            payload = data.get("payload", {})
            if agent == "Codex" and data.get("type") == "session_meta" and isinstance(payload, dict):
                cwd = str(payload.get("cwd") or cwd)
            elif agent == "Claude Code":
                cwd = str(data.get("cwd") or cwd)

            message = message_from_line(data, agent)
            if not message:
                continue
            role, text = message
            if role == "user":
                users.append(clip(text, limit))
            else:
                assistants.append(clip(text, limit))
        lines.close()
    except OSError as error:
        print(f"warning: cannot read {path}: {error}", file=sys.stderr)
        return None

    if not users:
        return None

    selected_users = [users[0]]
    if len(users) > 1:
        selected_users.extend(users[-2:])
    selected_users = list(dict.fromkeys(selected_users))

    session_time = min(timestamps) if timestamps else datetime.fromtimestamp(
        path.stat().st_mtime, tz=LOCAL_ZONE
    )
    return {
        "agent": agent,
        "time": session_time,
        "cwd": cwd,
        "path": path,
        "users": selected_users,
        "assistants": list(assistants),
    }


def session_paths(target: date) -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    claude_root = Path.home() / ".claude" / "projects"
    if claude_root.exists():
        for path in claude_root.rglob("*.jsonl"):
            if "subagents" in path.parts:
                continue
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=LOCAL_ZONE).date()
            if modified == target:
                paths.append(("Claude Code", path))

    codex_root = Path.home() / ".codex" / "sessions" / target.strftime("%Y/%m/%d")
    if codex_root.exists():
        for path in codex_root.glob("*.jsonl"):
            paths.append(("Codex", path))
    return paths


def quote(text: str) -> str:
    return "> " + text.replace("\n", "\n> ")


def render(target: date, sessions: list[dict[str, Any]]) -> str:
    lines = [f"# Session evidence for {target.isoformat()}", ""]
    for agent in ("Codex", "Claude Code"):
        matching = [session for session in sessions if session["agent"] == agent]
        lines.extend([f"## {agent} ({len(matching)})", ""])
        for session in matching:
            label = session["time"].strftime("%H:%M")
            cwd = f" — {session['cwd']}" if session["cwd"] else ""
            lines.extend([f"### {label}{cwd}", "", f"Source: `{session['path']}`", ""])
            lines.append("User requests:")
            for text in session["users"]:
                lines.extend(["", quote(text)])
            if session["assistants"]:
                lines.extend(["", "Last assistant text:"])
                for text in session["assistants"]:
                    lines.extend(["", quote(text)])
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=date.today().isoformat(), help="Local date: YYYY-MM-DD")
    parser.add_argument("--max-chars", type=int, default=2000, help="Maximum characters per message")
    parser.add_argument("--output", type=Path, help="Write Markdown here instead of stdout")
    args = parser.parse_args()

    try:
        target = date.fromisoformat(args.date)
    except ValueError:
        parser.error("--date must use YYYY-MM-DD")

    sessions = [
        session
        for agent, path in session_paths(target)
        if (session := collect_session(path, agent, args.max_chars))
    ]
    sessions.sort(key=lambda session: session["time"])
    output = render(target, sessions)

    if args.output:
        args.output.expanduser().write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
