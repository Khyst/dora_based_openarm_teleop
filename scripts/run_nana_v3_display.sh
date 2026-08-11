#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

echo "========================================================"
echo " Launching nana_v3_description RViz2 (Pixi Isolated Env)"
echo "========================================================"

if ! command -v pixi >/dev/null 2>&1; then
    echo "[Error] pixi command not found."
    echo "Please install pixi: curl -fsSL https://pixi.sh/install.sh | bash"
    
    if [ -f "/opt/ros/humble/setup.bash" ]; then
        echo "Falling back to system ROS2 Humble environment..."
        source /opt/ros/humble/setup.bash
        colcon build --packages-select nana_v3_description
        source install/setup.bash
        ros2 launch nana_v3_description display.launch.py "$@"
        exit 0
    else
        exit 1
    fi
fi

echo "[1/3] Synchronizing pixi environment..."
pixi install

echo "[2/3] Building nana_v3_description package with colcon..."
pixi run build-v3

echo "[3/3] Launching RViz2 display..."
pixi run display-v3 "$@"
