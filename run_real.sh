#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"

echo "[NANA Teleop Real] Starting Dora real robot dataflow locally using 'dora run'..."
uv run dora run "$SCRIPT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop.yaml"
