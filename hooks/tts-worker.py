#!/usr/bin/env python3
"""
save-my-eyesight: per-session TTS queue worker.

Single-instance per session (flock). Drains /tmp/sme-queue-<sid>/ in lex order,
speaking each chunk synchronously via macOS `say`. Exits after IDLE_TIMEOUT
seconds with no new chunks so it doesn't linger.

Killed indirectly when stop-tts.sh pkills `say` and clears the queue dir.
"""
from __future__ import annotations

import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path


IDLE_TIMEOUT = 30.0
POLL = 0.15
TMP = Path("/tmp")


def pop_chunk(queue_dir: Path) -> str | None:
    if not queue_dir.exists():
        return None
    try:
        files = sorted(p for p in queue_dir.iterdir() if p.is_file())
    except FileNotFoundError:
        return None
    if not files:
        return None
    f = files[0]
    try:
        text = f.read_text()
        f.unlink()
        return text
    except FileNotFoundError:
        return None


def speak(text: str) -> None:
    voice = os.environ.get("SME_VOICE", "Noelle (Enhanced)").strip()
    rate = os.environ.get("SME_RATE", "260").strip()
    cmd = ["say"]
    if voice:
        cmd += ["-v", voice]
    if rate:
        cmd += ["-r", rate]
    cmd.append(text)
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    sid = sys.argv[1]
    queue_dir = TMP / f"sme-queue-{sid}"
    lock_path = TMP / f"sme-worker-{sid}.lock"

    lf = lock_path.open("w")
    try:
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0

    idle = 0.0
    while idle < IDLE_TIMEOUT:
        chunk = pop_chunk(queue_dir)
        if chunk and chunk.strip():
            speak(chunk)
            idle = 0.0
            continue
        time.sleep(POLL)
        idle += POLL
    return 0


if __name__ == "__main__":
    sys.exit(main())
