#!/usr/bin/env bash
# Thin wrapper around `python -m baebugs.doctor`. Extra args pass through (--quick, --json out.json).
# gum (if installed and on a terminal) only adds a header/spinner; plain output otherwise.
# Exits non-zero if any check FAILs.
set -u
cd "$(dirname "$0")/.." || exit 2
PY="${PYTHON:-python3}"
if command -v gum >/dev/null 2>&1 && [ -t 1 ]; then
  gum style --border rounded --padding "0 2" "baebugs doctor" || true
  tmp="$(mktemp)"
  gum spin --spinner dot --title "running checks..." -- sh -c "\"$PY\" -m baebugs.doctor \"\$@\" >\"$tmp\" 2>&1" sh "$@"
  cat "$tmp"
  # exit status comes from the report itself, not from gum
  if grep -Eq '^[0-9]+ PASS, [1-9][0-9]* FAIL' "$tmp"; then rc=1; else rc=0; fi
  grep -q ' PASS, .* FAIL, ' "$tmp" || rc=1
  rm -f "$tmp"
else
  "$PY" -m baebugs.doctor "$@"
  rc=$?
fi
exit $rc
