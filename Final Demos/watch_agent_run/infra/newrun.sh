#!/bin/bash
# newrun.sh — scaffold a run folder.
#
#   ./infra/newrun.sh 3            # makes run_3/ next to infra/
#   ./infra/newrun.sh 3 no_pc      # makes run_3_no_pc/
#
# Creates the folder, two empty stubs, and an env snapshot taken NOW (server,
# version, skill size) so the run's conditions are recorded before they drift.
# Opens the spec for editing if $EDITOR is set.

set -euo pipefail

N="${1:-}"
SUFFIX="${2:-}"
if [ -z "$N" ]; then
  echo "usage: $0 <run-number> [suffix]" >&2
  exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
DIR="$ROOT/run_${N}${SUFFIX:+_$SUFFIX}"

if [ -d "$DIR" ]; then
  echo "already exists: $DIR" >&2
  exit 1
fi
mkdir -p "$DIR"

cat > "$DIR/spec_$N.md" <<EOF
# Run $N — spec

Date: $(date -Iseconds)

## Prompt(s)

[PASTE IN HERE, IN ORDER, BEFORE PASTING INTO CLAUDE CODE]

Initial prompt:

---

Additional prompts:

EOF

cat > "$DIR/reported_runtime_$N.md" <<EOF
# Run $N Reported Runtime

[XXX REPLACE WITH REPORTED RUNTIME]
EOF

# Environment snapshot — taken now, not reconstructed later.
{
  echo "# Run $N — environment at scaffold time"
  echo "date: $(date -Iseconds)"
  echo
  echo "## paperclip config"
  paperclip config 2>&1 || echo "(paperclip config failed)"
  echo
  echo "## paperclip version"
  paperclip update 2>&1 | head -3 || echo "(paperclip update failed)"
  echo
  echo "## skill files on disk"
  for f in "$HOME/.claude/skills/paperclip/SKILL.md" ".claude/skills/paperclip/SKILL.md"; do
    [ -f "$f" ] && echo "$(wc -c < "$f") bytes  $f"
  done
} > "$DIR/env_$N.txt" 2>&1

echo "created $DIR"
ls -1 "$DIR" | sed 's/^/  /'
echo
echo "when the run finishes:"
echo "  $HERE/finishrun.sh $N${SUFFIX:+ $SUFFIX}"

if [ -n "${EDITOR:-}" ]; then
  "$EDITOR" "$DIR/spec_$N.md" || true
fi
