#!/usr/bin/env bash
# Fires on UserPromptSubmit. Cuts off in-flight speech AND clears the queue
# so stale chunks from the prior assistant turn don't keep playing.
pkill -x say 2>/dev/null

# session_id arrives via stdin JSON. Use python for portable JSON parsing.
sid="$(python3 -c 'import json,sys
try:
    print(json.load(sys.stdin).get("session_id") or "")
except Exception:
    pass' 2>/dev/null)"

if [ -n "$sid" ]; then
  rm -rf "/tmp/sme-queue-$sid" 2>/dev/null
  rm -f  "/tmp/sme-marker-$sid.txt" 2>/dev/null
fi

exit 0
