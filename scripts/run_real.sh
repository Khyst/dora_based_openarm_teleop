#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
export CMAKE_PREFIX_PATH="$HOME/.local:$CMAKE_PREFIX_PATH"

# Auto-run setup if virtual environment is missing
if [ ! -d "$ROOT_DIR/.venv" ]; then
    echo "[NANA Teleop] Initializing workspace environment..."
    "$SCRIPT_DIR/setup_env.sh"
fi

echo "[NANA Teleop Real] Starting Dora real robot teleoperation dataflow locally..."
echo "  - URDF/XML Model: nana_v3_description"
echo "  - Follower Arms: Left & Right OpenArm Hardware"
echo "  - UDP Listener: 0.0.0.0:5006 (Meta Quest VR)"
echo "  - Web UI: http://localhost:8000"
echo "  - Press Ctrl+C to stop"
echo ""

cd "$ROOT_DIR"
uv run dora run "$ROOT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop.yaml"
