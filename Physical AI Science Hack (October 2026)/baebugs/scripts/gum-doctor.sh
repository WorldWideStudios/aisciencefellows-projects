#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if command -v gum >/dev/null 2>&1; then gum style --foreground 212 --bold "Baebugs AoK doctor · interactive wrapper"; else echo "Baebugs AoK doctor"; fi
python3 tools/aok_build.py doctor
node packages/baebugs-aok/bin/baebugs-aok.mjs verify
node --check site/aok/app.js
if command -v pytest >/dev/null 2>&1; then PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_aok_evidence.py; else echo "pytest NOT_TESTED: binary missing"; fi
echo "GUM_DOCTOR_WRAPPER PASS; gum itself has no doctor subcommand."
