#!/usr/bin/env bash
# Install K-Dense scientific-agent-skills into the project (Cursor Agent Skills).
# Usage: bash scripts/install-scientific-skills.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${SCIENTIFIC_SKILLS_DIR:-${REPO_ROOT}/.cursor/skills/scientific-agent-skills}"
REF="${SCIENTIFIC_SKILLS_REF:-main}"
GIT_URL="https://github.com/K-Dense-AI/scientific-agent-skills.git"

if [[ -d "${SKILLS_DIR}/.git" ]]; then
  echo "Updating scientific-agent-skills at ${SKILLS_DIR}"
  git -C "${SKILLS_DIR}" fetch --depth 1 origin "${REF}"
  git -C "${SKILLS_DIR}" checkout "${REF}"
  git -C "${SKILLS_DIR}" pull --ff-only origin "${REF}" 2>/dev/null || true
else
  mkdir -p "$(dirname "${SKILLS_DIR}")"
  echo "Cloning scientific-agent-skills into ${SKILLS_DIR}"
  git clone --depth 1 --branch "${REF}" "${GIT_URL}" "${SKILLS_DIR}"
fi

echo "Installed K-Dense scientific-agent-skills at ${SKILLS_DIR}"
echo "Key skills: paper-lookup, database-lookup, literature-review"
