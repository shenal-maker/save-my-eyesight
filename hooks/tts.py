#!/usr/bin/env python3
"""
save-my-eyesight: chunked TTS hook for Claude Code.

Wired to both PreToolUse and Stop. Each fire:
  1. Read transcript tail to find assistant text written since the last "spoken" marker.
  2. Enqueue new text for the per-session worker (tts-worker.py) to speak sequentially.
  3. Update the marker.

State files per session under /tmp:
  sme-marker-<sid>.txt        last spoken assistant uuid
  sme-queue-<sid>/             dir of chunk files, lex-sorted
  sme-hook-<sid>.lock          flock for the critical section
  sme-worker-<sid>.lock        flock owned by the running worker

Env vars:
  SME_VOICE   macOS voice name (default: Noelle (Enhanced)). See `say -v ?`.
  SME_RATE    words per minute (default: 260).
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
WORKER = HERE / "tts-worker.py"
TMP = Path("/tmp")


def state_paths(sid: str):
    return (
        TMP / f"sme-marker-{sid}.txt",
        TMP / f"sme-queue-{sid}",
        TMP / f"sme-hook-{sid}.lock",
    )


def read_marker(marker: Path) -> str:
    try:
        return marker.read_text().strip()
    except FileNotFoundError:
        return ""


def write_marker(marker: Path, uuid: str) -> None:
    marker.write_text(uuid)


def find_unsaid_assistant_text(transcript_path: Path, last_uuid: str) -> tuple[str, str]:
    """Return (concatenated text after last_uuid, newest assistant uuid seen).
    If last_uuid is empty, only speaks the most recent assistant entry to avoid
    flooding on first run mid-session.
    """
    if not transcript_path.exists():
        return "", last_uuid

    assistants: list[tuple[str, str]] = []  # (uuid, text)
    with transcript_path.open() as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "assistant":
                continue
            if entry.get("isSidechain"):
                continue
            uuid = entry.get("uuid") or ""
            content = entry.get("message", {}).get("content")
            if not isinstance(content, list):
                continue
            parts = [b.get("text", "") for b in content
                     if isinstance(b, dict) and b.get("type") == "text"]
            text = "\n".join(p for p in parts if p).strip()
            if text:
                assistants.append((uuid, text))

    if not assistants:
        return "", last_uuid

    if not last_uuid:
        uuid, text = assistants[-1]
        return text, uuid

    new_items: list[tuple[str, str]] = []
    seen_marker = False
    for uuid, text in assistants:
        if seen_marker:
            new_items.append((uuid, text))
        elif uuid == last_uuid:
            seen_marker = True
    if not seen_marker:
        uuid, text = assistants[-1]
        return text, uuid

    if not new_items:
        return "", last_uuid

    combined = "\n".join(t for _, t in new_items)
    newest_uuid = new_items[-1][0]
    return combined, newest_uuid


def strip_for_ear(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " code block omitted. ", text)
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*\n]+)\*", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\n{2,}", ". ", text)
    return text.strip()


def enqueue(queue_dir: Path, text: str) -> None:
    queue_dir.mkdir(exist_ok=True)
    name = f"{time.time():.6f}-{os.getpid()}.txt"
    (queue_dir / name).write_text(text)


def ensure_worker(sid: str) -> None:
    subprocess.Popen(
        ["python3", str(WORKER), sid],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    transcript_path = payload.get("transcript_path")
    sid = payload.get("session_id") or "default"
    if not transcript_path:
        return 0

    marker_path, queue_dir, hook_lock = state_paths(sid)

    with hook_lock.open("w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        last_uuid = read_marker(marker_path)
        text, newest_uuid = find_unsaid_assistant_text(Path(transcript_path), last_uuid)
        if not text.strip():
            return 0
        spoken = strip_for_ear(text)
        if not spoken:
            write_marker(marker_path, newest_uuid)
            return 0
        enqueue(queue_dir, spoken)
        write_marker(marker_path, newest_uuid)

    ensure_worker(sid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
