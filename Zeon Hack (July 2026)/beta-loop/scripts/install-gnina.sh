#!/usr/bin/env bash
# GNINA is not on PyPI. Use a pre-built binary (Linux/WSL) or Docker.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== GNINA install helper ==="
echo
echo "GNINA requires CUDA on Linux or WSL2. There is no native macOS binary."
echo "Options:"
echo
echo "1) Pre-built binary (Linux / WSL2 Ubuntu 22.04)"
echo "   https://github.com/gnina/gnina/releases/latest"
echo "   export GNINA_BIN=/path/to/gnina"
echo
echo "2) Docker (recommended on macOS with Colima/Docker Desktop + NVIDIA if available)"
echo "   docker pull gnina/gnina:latest"
echo "   # Example single compound (mount repo + local docking output):"
echo "   docker run --rm -v \"\$PWD:/work\" -w /work gnina/gnina:latest \\"
echo "     gnina -r pvjthomas/local/docking/_receptor/1JQL_receptor.pdb \\"
echo "           -l pvjthomas/local/docking/T0138/ligand.sdf \\"
echo "           --autobox_ligand pvjthomas/local/docking/_receptor/1JQL_autobox.pdb \\"
echo "           -o pvjthomas/local/docking/T0138/docked.sdf"
echo
echo "3) Build from source — see https://github.com/gnina/gnina#installation"
echo
echo "After install, verify:"
echo "  gnina --help   # or: \$GNINA_BIN --help"
echo
echo "Then run batch docking from repo root:"
echo "  source .venv/bin/activate"
echo "  python -c \"import sys; sys.path.insert(0,'ml'); from agent.tools.reverse import run_gnina_batch, rank_by_dock_score; run_gnina_batch(); rank_by_dock_score(top_n=8)\""
echo

if command -v gnina >/dev/null 2>&1; then
  echo "Found gnina: $(command -v gnina)"
  gnina --help | head -5
elif [[ -n "${GNINA_BIN:-}" && -x "${GNINA_BIN}" ]]; then
  echo "Found GNINA_BIN=${GNINA_BIN}"
  "${GNINA_BIN}" --help | head -5
else
  echo "gnina not found on PATH and GNINA_BIN is unset."
fi
