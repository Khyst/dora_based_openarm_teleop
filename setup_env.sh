#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"
export CMAKE_PREFIX_PATH="$HOME/.local:$CMAKE_PREFIX_PATH"

echo "=== [NANA Teleop WS] Environment Setup & Verification ==="

# 1. Ensure uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "[1/3] Installing uv package manager..."
    python3 -m pip install --user uv
else
    echo "[1/3] uv package manager is available."
fi

# 2. Ensure CLI11 CMake package is available for openarm-can build
if [ ! -f "$HOME/.local/share/cmake/CLI11/CLI11Config.cmake" ] && \
   [ ! -f "/usr/lib/cmake/CLI11/CLI11Config.cmake" ] && \
   [ ! -f "/usr/share/cmake/CLI11/CLI11Config.cmake" ] && \
   [ ! -f "/usr/local/share/cmake/CLI11/CLI11Config.cmake" ]; then
    echo "[2/3] CLI11 CMake package not found. Automatically fetching and installing CLI11..."
    CLI11_TMP=$(mktemp -d)
    curl -sSL https://github.com/CLIUtils/CLI11/archive/refs/tags/v2.4.2.tar.gz | tar -xz -C "$CLI11_TMP"
    cmake -S "$CLI11_TMP/CLI11-2.4.2" -B "$CLI11_TMP/build" \
        -DCMAKE_INSTALL_PREFIX="$HOME/.local" \
        -DCLI11_BUILD_TESTS=OFF \
        -DCLI11_BUILD_EXAMPLES=OFF >/dev/null 2>&1
    cmake --install "$CLI11_TMP/build" >/dev/null 2>&1
    rm -rf "$CLI11_TMP"
    echo "      CLI11 installed successfully to ~/.local."
else
    echo "[2/3] CLI11 C++ dependency is available."
fi

# 3. Synchronize Python workspace (8 sub-packages)
echo "[3/3] Synchronizing all workspace packages with uv sync..."
uv sync

echo "=== Setup complete! ==="
