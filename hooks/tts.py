#!/usr/bin/env python3
"""
save-my-eyesight: Stop hook for Claude Code.

Reads the most recent assistant message from the session transcript and
speaks it through macOS `say`. Strips markdown decoration that doesn't
translate to speech (code blocks, headers, bullets, link URLs).

Env vars:
  SME_VOICE   macOS voice name (default: system voice). See `say -v ?`.
  SME_RATE    words per minute (default: 220).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def find_last_assistant_text(transcript_path: Path) -> str:
    if not transcript_path.exists():
        return ""
    with transcript_path.open() as f:
        lines = f.readlines()
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        parts = [b.get("text", "") for b in content if b.get("type") == "text"]
        joined = "\n".join(p for p in parts if p)
        if joined.strip():
            return joined
    return ""


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


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    transcript_path = payload.get("transcript_path")
    if not transcript_path:
        return 0

    text = find_last_assistant_text(Path(transcript_path))
    if not text:
        return 0

    spoken = strip_for_ear(text)
    if not spoken:
        return 0

    # Cut off any in-flight speech so the latest reply takes over immediately.
    subprocess.run(["pkill", "-x", "say"], stderr=subprocess.DEVNULL)

    cmd = ["say"]
    voice = os.environ.get("SME_VOICE", "").strip()
    if voice:
        cmd += ["-v", voice]
    rate = os.environ.get("SME_RATE", "220").strip()
    if rate:
        cmd += ["-r", rate]
    cmd.append(spoken)

    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
