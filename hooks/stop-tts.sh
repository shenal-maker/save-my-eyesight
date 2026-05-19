#!/usr/bin/env bash
# Kill any in-flight `say` so a fresh user prompt stops the previous reply mid-sentence.
pkill -x say 2>/dev/null
exit 0
