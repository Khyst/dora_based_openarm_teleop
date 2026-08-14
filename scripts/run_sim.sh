#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Visualizer option parsing (default: foxglove)
VISUALIZER="mujoco"
while [[ $# -gt 0 ]]; do
  case $1 in
    --visualizer|-v)
      VISUALIZER="$2"
      shift 2
      ;;
    mujoco|foxglove)
      VISUALIZER="$1"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [foxglove|mujoco] [--visualizer foxglove|mujoco]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [foxglove|mujoco] [--visualizer foxglove|mujoco]"
      exit 1
      ;;
  esac
done

if [ "$VISUALIZER" != "foxglove" ] && [ "$VISUALIZER" != "mujoco" ]; then
    echo "❌ Error: Invalid visualizer '$VISUALIZER'. Options: 'foxglove', 'mujoco'"
    exit 1
fi

DATAFLOW_FILE="$ROOT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop-sim-${VISUALIZER}.yaml"

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

echo "[NANA Teleop Sim] Starting Dora simulation dataflow locally..."
echo "  - URDF/XML Model: nana_v3_description"
echo "  - Visualizer: $VISUALIZER"
if [ "$VISUALIZER" == "foxglove" ]; then
    echo "  - Foxglove Visualizer: ws://localhost:8765 (Foxglove Studio: https://app.foxglove.dev)"
else
    echo "  - MuJoCo GUI Viewer: Passive 3D Window"
fi
echo "  - UDP Listener: 0.0.0.0:5006 (Meta Quest VR)"
echo "  - Press Ctrl+C to stop"
echo ""

cd "$ROOT_DIR"
"$ROOT_DIR/.venv/bin/dora" run "$DATAFLOW_FILE"
