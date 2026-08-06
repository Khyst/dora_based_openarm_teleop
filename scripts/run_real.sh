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

export TLS_CERTIFICATE_FILE="${TLS_CERTIFICATE_FILE:-$ROOT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-webxr/example/server.crt}"
export TLS_KEY_FILE="${TLS_KEY_FILE:-$ROOT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-webxr/example/server.key}"

MODE="${1:-webxr}"

case "$MODE" in
    webxr)
        FLOW_FILE="$ROOT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-webxr.yaml"
        RECEIVER_DESC="WebXR Server (https://<host>:8443)"
        ;;
    quest|quest_receiver)
        FLOW_FILE="$ROOT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop.yaml"
        RECEIVER_DESC="UDP Quest Receiver (0.0.0.0:5006)"
        ;;
    *)
        echo "[NANA Teleop Real] Error: Invalid mode '$MODE'. Use 'webxr' (default) or 'quest' / 'quest_receiver'."
        exit 1
        ;;
esac

echo "[NANA Teleop Real] Starting Dora real robot teleoperation dataflow locally..."
echo "  - Mode: $MODE"
echo "  - Receiver: $RECEIVER_DESC"
echo "  - URDF/XML Model: nana_v3_description"
echo "  - Follower Arms: Left & Right OpenArm Hardware"
echo "  - Web UI: http://localhost:8000"
echo "  - Flow file: $FLOW_FILE"
echo "  - Press Ctrl+C to stop"
echo ""

cd "$ROOT_DIR"
"$ROOT_DIR/.venv/bin/dora" run "$FLOW_FILE"
