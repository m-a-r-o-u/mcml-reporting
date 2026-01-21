#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but was not found in PATH." >&2
  echo "Install uv first: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

uv venv
# shellcheck disable=SC1091
source .venv/bin/activate

uv pip install "git+ssh://git@github.com/m-a-r-o-u/sim.git"
uv pip install "git+ssh://git@github.com/m-a-r-o-u/slurm.git"

uv pip install -e .

echo "Setup complete. Activate with: source .venv/bin/activate"
