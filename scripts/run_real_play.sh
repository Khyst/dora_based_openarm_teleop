#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# Auto-run setup if virtual environment is missing
if [ ! -d "$ROOT_DIR/.venv" ]; then
    echo "[NANA Teleop] Initializing workspace environment..."
    "$SCRIPT_DIR/setup_env.sh"
fi

unset VIRTUAL_ENV
if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
    source "$ROOT_DIR/.venv/bin/activate"
fi
export PATH="$ROOT_DIR/.venv/bin:$HOME/.local/bin:$PATH"
export CMAKE_PREFIX_PATH="$HOME/.local:$CMAKE_PREFIX_PATH"

echo "[NANA Teleop Real Play] Replaying recorded VR UDP dataflow on real robot hardware..."
echo "  - URDF/XML Model: nana_v3_description"
echo "  - Recorded File: recordings/vr_real_session.jsonl"
echo "  - Web UI: http://localhost:8000"
echo "  - Press Ctrl+C to stop"
echo ""

cd "$ROOT_DIR"
uv run dora run "$ROOT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-play.yaml"
