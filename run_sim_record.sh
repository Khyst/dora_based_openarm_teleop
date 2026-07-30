#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"
export CMAKE_PREFIX_PATH="$HOME/.local:$CMAKE_PREFIX_PATH"

# Auto-run setup if virtual environment is missing
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "[NANA Teleop] Initializing workspace environment..."
    "$SCRIPT_DIR/setup_env.sh"
fi

echo "[NANA Teleop Sim Record] Starting Dora simulation dataflow with VR UDP recording..."
echo "  - URDF/XML Model: nana_v3_description"
echo "  - UDP Listener: 0.0.0.0:5006 (Meta Quest VR)"
echo "  - Record File: recordings/vr_sim_session.jsonl"
echo "  - Web UI: http://localhost:8000"
echo "  - Press Ctrl+C to stop"
echo ""

uv run dora run "$SCRIPT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-sim-record.yaml"
