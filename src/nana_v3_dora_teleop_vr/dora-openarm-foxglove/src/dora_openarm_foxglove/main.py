"""Dora node entry point for Foxglove Studio visualization."""

from __future__ import annotations

import argparse
import asyncio
import datetime
import logging
import pathlib
import signal
import sys
import threading
import time
from typing import Any

import dora
import numpy as np
import pyarrow as pa

from .server import FoxgloveVisualizerServer, MeshAssetServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dora_openarm_foxglove")


def extract_values(value: Any, key: str = "qpos") -> np.ndarray:
    """Read `key` from a length-1 StructArray, or a flat array as-is."""
    if hasattr(value, "type") and pa.types.is_struct(value.type):
        if key in value.type.names:
            val = value.field(key)[0]
        elif "new_position" in value.type.names:
            val = value.field("new_position")[0]
        elif "pose" in value.type.names:
            val = value.field("pose")[0]
        elif "qpos" in value.type.names:
            val = value.field("qpos")[0]
        else:
            val = value.field(0)[0]
        if hasattr(val, "values"):
            return np.array(val.values, dtype=np.float32)
        return np.array(val, dtype=np.float32)
    return np.array(value, dtype=np.float32).flatten()


def extract_float(value: Any) -> float:
    """Extract a single float value from pa.Array or numpy array."""
    if isinstance(value, pa.Array):
        return float(value[0].as_py())
    arr = np.asarray(value).flatten()
    return float(arr[0]) if len(arr) > 0 else 0.0


def extract_bool(value: Any) -> bool:
    """Extract a boolean value from pa.Array or numpy array."""
    if isinstance(value, pa.Array):
        return bool(value[0].as_py())
    arr = np.asarray(value).flatten()
    return bool(arr[0]) if len(arr) > 0 else False


def parse_timestamp_ns(metadata: dict[str, Any] | None) -> int:
    """Extract or calculate nanosecond timestamp from event metadata."""
    if metadata and "timestamp" in metadata:
        ts = metadata["timestamp"]
        if isinstance(ts, (int, float)):
            return int(ts)
        elif isinstance(ts, datetime.datetime):
            return int(ts.timestamp() * 1_000_000_000)
    return time.time_ns()


def dora_event_loop(
    node: dora.Node,
    foxglove_server: FoxgloveVisualizerServer,
    stop_event: threading.Event,
) -> None:
    """Dora event polling loop running in a dedicated worker thread."""
    logger.info("Dora event listener loop started.")

    # Send ready status
    try:
        node.send_output("status", pa.array(["ready"]))
    except Exception as e:
        logger.warning(f"Could not send startup status output: {e}")

    try:
        for event in node:
            if stop_event.is_set():
                break

            if event["type"] != "INPUT":
                continue

            eid = event["id"]
            val = event["value"]
            metadata = event.get("metadata")
            ts_ns = parse_timestamp_ns(metadata)

            if eid == "position_left":
                qpos = extract_values(val, key="qpos")
                foxglove_server.update_joint_positions("left", qpos, timestamp_ns=ts_ns)

            elif eid == "position_right":
                qpos = extract_values(val, key="qpos")
                foxglove_server.update_joint_positions("right", qpos, timestamp_ns=ts_ns)

            elif eid == "pose_right":
                pose = extract_values(val, key="pose")
                foxglove_server.update_transform("quest_controller_right", pose, timestamp_ns=ts_ns)

            elif eid == "pose_left":
                pose = extract_values(val, key="pose")
                foxglove_server.update_transform("quest_controller_left", pose, timestamp_ns=ts_ns)

            elif eid == "pose_reference":
                pose = extract_values(val, key="pose")
                foxglove_server.update_transform("quest_headset", pose, timestamp_ns=ts_ns)

            elif eid == "trigger_left":
                pct = round(extract_float(val) * 100.0, 2)
                foxglove_server.update_quest_input("trigger_left_pct", pct, timestamp_ns=ts_ns)

            elif eid == "trigger_right":
                pct = round(extract_float(val) * 100.0, 2)
                foxglove_server.update_quest_input("trigger_right_pct", pct, timestamp_ns=ts_ns)

            elif eid == "button_a":
                b_val = extract_bool(val)
                foxglove_server.update_quest_input("button_a", b_val, timestamp_ns=ts_ns)

            elif eid == "button_b":
                b_val = extract_bool(val)
                foxglove_server.update_quest_input("button_b", b_val, timestamp_ns=ts_ns)

            elif eid == "button_x":
                b_val = extract_bool(val)
                foxglove_server.update_quest_input("button_x", b_val, timestamp_ns=ts_ns)

            elif eid == "button_y":
                b_val = extract_bool(val)
                foxglove_server.update_quest_input("button_y", b_val, timestamp_ns=ts_ns)

    except Exception as e:
        logger.error(f"Error in Dora event loop: {e}", exc_info=True)
    finally:
        logger.info("Dora event listener loop stopping.")
        stop_event.set()


async def run_server(
    host: str,
    port: int,
    urdf_path: pathlib.Path | None,
    mesh_http_port: int,
    mesh_asset_server: MeshAssetServer | None,
    stop_event: threading.Event,
) -> None:
    """Async main task managing FoxgloveServer lifecycle."""
    if mesh_asset_server is not None:
        mesh_asset_server.start()

    server_mgr = FoxgloveVisualizerServer(
        host=host,
        port=port,
        urdf_path=urdf_path,
        mesh_http_port=mesh_http_port,
    )
    server_mgr.loop = asyncio.get_running_loop()
    server = server_mgr.get_server()

    logger.info(f"Starting Foxglove WebSocket server on ws://{host}:{port}...")

    # Initialize Dora Node
    try:
        node = dora.Node()
    except Exception as e:
        logger.warning(f"Could not connect to Dora runtime ({e}). Running in standalone test mode.")
        node = None

    async with server:
        await server_mgr.setup_channels()
        logger.info(f"Foxglove server is live and listening on ws://{host}:{port}")

        if node is not None:
            thread = threading.Thread(
                target=dora_event_loop,
                args=(node, server_mgr, stop_event),
                daemon=True,
            )
            thread.start()

        # Keep server running until stop_event is triggered
        while not stop_event.is_set():
            await asyncio.sleep(0.1)

    if mesh_asset_server is not None:
        mesh_asset_server.stop()
    logger.info("Foxglove server shut down cleanly.")


def _find_default_urdf() -> tuple[pathlib.Path | None, pathlib.Path | None]:
    """Locate default nana_v3_corrected.urdf and nana_v3_description directory."""
    # Current script: src/nana_v3_dora_teleop_vr/dora-openarm-foxglove/src/dora_openarm_foxglove/main.py
    # Root: 4 levels up from this file, or workspace root
    base = pathlib.Path(__file__).resolve().parent
    for _ in range(6):
        candidate_desc = base / "src" / "nana_v3_description"
        candidate_urdf = candidate_desc / "assets" / "robot" / "urdf" / "nana_v3_corrected.urdf"
        if candidate_urdf.exists():
            return candidate_urdf, candidate_desc
        # Also check relative to workspace
        candidate_desc2 = base / "nana_v3_description"
        candidate_urdf2 = candidate_desc2 / "assets" / "robot" / "urdf" / "nana_v3_corrected.urdf"
        if candidate_urdf2.exists():
            return candidate_urdf2, candidate_desc2
        base = base.parent
    return None, None


def main() -> None:
    """CLI entry point."""
    default_urdf, default_mesh_dir = _find_default_urdf()

    parser = argparse.ArgumentParser(description="Foxglove WebSocket Visualizer Dora Node")
    parser.add_argument("--host", default="0.0.0.0", help="Foxglove WebSocket server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Foxglove WebSocket server port (default: 8765)")
    parser.add_argument("--urdf", default=str(default_urdf) if default_urdf else None, help="Path to URDF robot description file")
    parser.add_argument("--mesh-dir", default=str(default_mesh_dir) if default_mesh_dir else None, help="Path to mesh package directory")
    parser.add_argument("--mesh-http-port", type=int, default=8766, help="HTTP port for serving 3D mesh assets (default: 8766)")
    args = parser.parse_args()

    stop_event = threading.Event()

    def _sig_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        stop_event.set()

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    urdf_path = pathlib.Path(args.urdf) if args.urdf else None
    mesh_dir = pathlib.Path(args.mesh_dir) if args.mesh_dir else None
    mesh_asset_server = MeshAssetServer(mesh_dir, port=args.mesh_http_port) if mesh_dir else None

    try:
        asyncio.run(
            run_server(
                host=args.host,
                port=args.port,
                urdf_path=urdf_path,
                mesh_http_port=args.mesh_http_port,
                mesh_asset_server=mesh_asset_server,
                stop_event=stop_event,
            )
        )
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
