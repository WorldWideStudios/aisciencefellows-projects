#!/bin/bash
# finishrun.sh — pull the session log into a run folder and process it.
#
#   ./infra/finishrun.sh 3                  # newest session log
#   ./infra/finishrun.sh 3 no_pc            # newest, into run_3_no_pc/
#   ./infra/finishrun.sh 3 -- 3920e25a-...  # a specific session id
#   ./infra/finishrun.sh 3 no_pc 3920e25a-...
#
# Writes into the run folder:
#   session_N.jsonl        the raw log, copied verbatim
#   trace_N.md             cc_trace.py    — every call and its result
#   strip_N.svg            strip_one.py   — call kinds + trust borders
#   artifact_trace_N.md    artifact_trace.py — where each artifact's bytes came from
#   SKILL_N.md             the skill text this run actually loaded
#   env_N.txt              appended: environment at finish time
#
# .txt renderings are not written — regenerate any time with:
#   python3 infra/cc_trace.py session_N.jsonl
#   python3 infra/strip_one.py session_N.jsonl --label run_N --print

set -euo pipefail

N="${1:-}"
if [ -z "$N" ]; then
  echo "usage: $0 <run-number> [suffix] [session-id]" >&2
  exit 1
fi
shift

SUFFIX=""
SESSION_ID=""
for arg in "$@"; do
  case "$arg" in
    --) ;;
    *-*-*-*-*) SESSION_ID="$arg" ;;
    *) SUFFIX="$arg" ;;
  esac
done

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
DIR="$ROOT/run_${N}${SUFFIX:+_$SUFFIX}"
[ -d "$DIR" ] || { echo "no such run folder: $DIR" >&2; exit 1; }

# Claude Code stores logs under a directory named for the launch path,
# with slashes turned into hyphens.
PROJ_DIR="$HOME/.claude/projects/$(pwd | sed 's|/|-|g')"
[ -d "$PROJ_DIR" ] || PROJ_DIR=""

if [ -n "$SESSION_ID" ]; then
  if [ -n "$PROJ_DIR" ] && [ -f "$PROJ_DIR/$SESSION_ID.jsonl" ]; then
    SRC="$PROJ_DIR/$SESSION_ID.jsonl"
  else
    SRC="$(find "$HOME/.claude/projects" -name "$SESSION_ID.jsonl" -print -quit 2>/dev/null || true)"
  fi
  [ -n "$SRC" ] || { echo "session $SESSION_ID not found" >&2; exit 1; }
else
  SEARCH="${PROJ_DIR:-$HOME/.claude/projects}"
  SRC="$(ls -t "$SEARCH"/*.jsonl 2>/dev/null | head -1 || true)"
  [ -n "$SRC" ] || SRC="$(ls -t "$HOME"/.claude/projects/*/*.jsonl 2>/dev/null | head -1 || true)"
  [ -n "$SRC" ] || { echo "no session logs found" >&2; exit 1; }
  echo "using newest log: $(basename "$SRC")"
fi

cp "$SRC" "$DIR/session_$N.jsonl"
echo "copied -> $DIR/session_$N.jsonl"

cd "$DIR"
S="session_$N.jsonl"

echo
python3 "$HERE/cc_trace.py" "$S" --md > "trace_$N.md"
head -4 "trace_$N.md"
python3 "$HERE/strip_one.py" "$S" --label "run_$N" -o "strip_$N.svg" >/dev/null
python3 "$HERE/artifact_trace.py" "run_$N=$S" > "artifact_trace_$N.md"

if [ -f "$HERE/extract_skill.py" ]; then
  python3 "$HERE/extract_skill.py" "$S" -o "SKILL_$N.md" >/dev/null 2>&1 \
    && echo "skill loaded by this run: $(wc -c < "SKILL_$N.md") bytes" \
    || echo "no skill-loading call in this run"
fi

{
  echo
  echo "## environment at finish time — $(date -Iseconds)"
  paperclip config 2>&1 || true
  paperclip update 2>&1 | head -3 || true
} >> "env_$N.txt"

echo
python3 "$HERE/strip_one.py" "$S" --label "run_$N" --print
echo
cat "artifact_trace_$N.md"
echo
echo "wrote: session_$N.jsonl trace_$N.md strip_$N.svg artifact_trace_$N.md"
