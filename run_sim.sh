#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"

echo "[NANA Teleop Sim] Starting Dora simulation dataflow locally..."
echo "  - URDF/XML Model: nana_v3_description"
echo "  - UDP Listener: 0.0.0.0:5006 (Meta Quest VR)"
echo "  - Web UI: http://localhost:8000"
echo "  - Press Ctrl+C to stop"
echo ""

uv run dora run "$SCRIPT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-sim.yaml"
