#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Option parsing (default visualizer: web, default record-type: waypoints)
VISUALIZER="web"
RECORD_TYPE="${RECORD_TYPE:-waypoints}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --visualizer|-v)
      VISUALIZER="$2"
      shift 2
      ;;
    --record-type|-r)
      RECORD_TYPE="$2"
      shift 2
      ;;
    trajectories|waypoints)
      RECORD_TYPE="$1"
      shift
      ;;
    web)
      VISUALIZER="$1"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [web|mujoco|foxglove] [waypoints|trajectories] [--visualizer web|mujoco|foxglove] [--record-type waypoints|trajectories]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [web] [waypoints|trajectories] [--visualizer web] [--record-type waypoints|trajectories]"
      exit 1
      ;;
  esac
done

export RECORD_TYPE

if [ "$VISUALIZER" != "web" ]; then
    echo "❌ Error: Invalid visualizer '$VISUALIZER'. Options: 'web'"
    exit 1
fi

DATAFLOW_FILE="$ROOT_DIR/src/nana_v3_dora_teleop_vr/dora-openarm-vr/config/dataflow-nana-teleop.yaml"

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
echo "  - Record Type: $RECORD_TYPE"
echo "  - UDP Listener: 0.0.0.0:5006 (Meta Quest VR)"
echo "  - Press Ctrl+C to stop"
echo ""

cd "$ROOT_DIR"
"$ROOT_DIR/.venv/bin/dora" run "$DATAFLOW_FILE"