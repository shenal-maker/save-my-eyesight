#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_PATH="$REPO_DIR/hooks/tts.py"
STOP_PATH="$REPO_DIR/hooks/stop-tts.sh"
EAR_RULES="$REPO_DIR/prompts/ear-shaped.md"
SETTINGS="$HOME/.claude/settings.json"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
MARKER="<!-- save-my-eyesight: ear-shaped rules -->"

INSTALL_PROMPT=1
for arg in "$@"; do
  case "$arg" in
    --no-prompt) INSTALL_PROMPT=0 ;;
    -h|--help)
      cat <<USAGE
usage: ./install.sh [--no-prompt]

  (default)     wire TTS hook + append ear-shaped rules to ~/.claude/CLAUDE.md
  --no-prompt   wire TTS hook only, leave CLAUDE.md untouched
                (use this if you want ear-shaped rules per-project instead of global)
USAGE
      exit 0
      ;;
  esac
done

if [[ ! -f "$HOOK_PATH" ]]; then
  echo "missing $HOOK_PATH" >&2
  exit 1
fi
if [[ ! -f "$STOP_PATH" ]]; then
  echo "missing $STOP_PATH" >&2
  exit 1
fi
chmod +x "$HOOK_PATH" "$STOP_PATH"

mkdir -p "$(dirname "$SETTINGS")"
if [[ -f "$SETTINGS" ]]; then
  cp "$SETTINGS" "$SETTINGS.bak.$(date +%s)"
fi

python3 - "$SETTINGS" "$HOOK_PATH" "$STOP_PATH" <<'PY'
import json, os, sys
settings_path, hook_path, stop_path = sys.argv[1], sys.argv[2], sys.argv[3]
data = {}
if os.path.exists(settings_path):
    with open(settings_path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
hooks = data.setdefault("hooks", {})

def wire(event, cmd, label):
    bucket = hooks.setdefault(event, [])
    already = any(
        any(h.get("command") == cmd for h in group.get("hooks", []))
        for group in bucket
    )
    if already:
        print(f"{label} already wired")
        return False
    bucket.append({
        "matcher": ".*",
        "hooks": [{"type": "command", "command": cmd}],
    })
    print(f"wired {label}")
    return True

changed = False
changed |= wire("Stop", hook_path, f"Stop hook -> {hook_path}")
changed |= wire("PreToolUse", hook_path, f"PreToolUse hook -> {hook_path}")
changed |= wire("UserPromptSubmit", stop_path, f"UserPromptSubmit hook -> {stop_path}")
if changed:
    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)
PY

if [[ "$INSTALL_PROMPT" == "1" ]]; then
  if [[ ! -f "$CLAUDE_MD" ]] || ! grep -qF "$MARKER" "$CLAUDE_MD"; then
    {
      echo
      echo "$MARKER"
      cat "$EAR_RULES"
    } >> "$CLAUDE_MD"
    echo "appended ear-shaped rules -> $CLAUDE_MD"
  else
    echo "ear-shaped rules already present in $CLAUDE_MD"
  fi
else
  echo "skipped CLAUDE.md edits (--no-prompt)."
  echo "drop $EAR_RULES into a project's CLAUDE.md when you want ear-shaped replies for that project only."
fi

echo
echo "done. start a new Claude Code session — it should speak its next reply."
