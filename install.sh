#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_PATH="$REPO_DIR/hooks/tts.py"
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
chmod +x "$HOOK_PATH"

mkdir -p "$(dirname "$SETTINGS")"
if [[ -f "$SETTINGS" ]]; then
  cp "$SETTINGS" "$SETTINGS.bak.$(date +%s)"
fi

python3 - "$SETTINGS" "$HOOK_PATH" <<'PY'
import json, os, sys
settings_path, hook_path = sys.argv[1], sys.argv[2]
data = {}
if os.path.exists(settings_path):
    with open(settings_path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
stop = data.setdefault("hooks", {}).setdefault("Stop", [])
already = any(
    any(h.get("command") == hook_path for h in group.get("hooks", []))
    for group in stop
)
if already:
    print(f"Stop hook already wired -> {hook_path}")
else:
    stop.append({
        "matcher": ".*",
        "hooks": [{"type": "command", "command": hook_path}],
    })
    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wired Stop hook -> {hook_path}")
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
