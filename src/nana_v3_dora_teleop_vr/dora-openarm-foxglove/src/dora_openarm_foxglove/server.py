"""Foxglove WebSocket server manager and message serializer."""

from __future__ import annotations

import asyncio
import functools
import http.server
import json
import logging
import os
import pathlib
import threading
import time
from typing import Any

from foxglove_websocket.server import ChannelWithoutId, FoxgloveServer

from .schemas import (
    FRAME_TRANSFORMS_SCHEMA,
    JOINT_STATE_SCHEMA,
    QUEST_INPUTS_SCHEMA,
    ROBOT_DESCRIPTION_SCHEMA,
)

logger = logging.getLogger("dora_openarm_foxglove")

# Joint name mappings for OpenArm & NANA v3
OPENARM_LEFT_JOINTS = [f"openarm_left_joint{i}" for i in range(1, 8)] + [
    "openarm_left_finger_joint1",
    "openarm_left_finger_joint2",
]
OPENARM_RIGHT_JOINTS = [f"openarm_right_joint{i}" for i in range(1, 8)] + [
    "openarm_right_finger_joint1",
    "openarm_right_finger_joint2",
]
NANA_LEFT_JOINTS = [f"nana_v3_left_joint{i}" for i in range(1, 8)]
NANA_RIGHT_JOINTS = [f"nana_v3_right_joint{i}" for i in range(1, 8)]

ALL_JOINT_NAMES = (
    OPENARM_LEFT_JOINTS + OPENARM_RIGHT_JOINTS + NANA_LEFT_JOINTS + NANA_RIGHT_JOINTS
)


def _ns_to_timestamp_obj(timestamp_ns: int) -> dict[str, int]:
    """Convert nanoseconds to {sec, nsec} dict for Foxglove schemas."""
    return {
        "sec": timestamp_ns // 1_000_000_000,
        "nsec": timestamp_ns % 1_000_000_000,
    }


class CORSSimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Simple HTTP Request Handler with CORS headers enabled for mesh asset serving."""

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress standard access logging to keep console clean
        pass


class MeshAssetServer:
    """Lightweight HTTP Server serving 3D mesh assets with CORS."""

    def __init__(self, asset_dir: pathlib.Path, port: int = 8766):
        self.asset_dir = asset_dir
        self.port = port
        self.httpd: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.asset_dir.exists():
            logger.warning(f"Asset directory does not exist: {self.asset_dir}")
            return
        handler = functools.partial(CORSSimpleHTTPRequestHandler, directory=str(self.asset_dir))
        try:
            self.httpd = http.server.ThreadingHTTPServer(("0.0.0.0", self.port), handler)
            self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self._thread.start()
            logger.info(f"3D Mesh asset server started on http://0.0.0.0:{self.port} serving {self.asset_dir}")
        except Exception as e:
            logger.warning(f"Could not start mesh asset server on port {self.port}: {e}")

    def stop(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()


class FoxgloveVisualizerServer:
    """Foxglove WebSocket server handling live streams for joints, TF, URDF, and quest inputs."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        urdf_path: pathlib.Path | None = None,
        mesh_http_port: int = 8766,
    ):
        self.host = host
        self.port = port
        self.urdf_path = urdf_path
        self.mesh_http_port = mesh_http_port

        self.server: FoxgloveServer | None = None
        self.loop: asyncio.AbstractEventLoop | None = None

        self._joint_channel_id: int | None = None
        self._tf_channel_id: int | None = None
        self._quest_channel_id: int | None = None
        self._robot_desc_channel_id: int | None = None

        # Internal state caches
        self._left_qpos = [0.0] * 9
        self._right_qpos = [0.0] * 9

        # Initialize base frame transforms
        self._transforms: dict[str, dict[str, Any]] = {
            "nana_v3_body_link0": {
                "timestamp": _ns_to_timestamp_obj(0),
                "parent_frame_id": "world",
                "child_frame_id": "nana_v3_body_link0",
                "translation": {"x": 0.0, "y": 0.0, "z": 0.0},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            },
            "arm_origin": {
                "timestamp": _ns_to_timestamp_obj(0),
                "parent_frame_id": "world",
                "child_frame_id": "arm_origin",
                "translation": {"x": 0.0, "y": 0.0, "z": 1.22},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            },
        }

        self._quest_inputs = {
            "trigger_left_pct": 0.0,
            "trigger_right_pct": 0.0,
            "button_a": False,
            "button_b": False,
            "button_x": False,
            "button_y": False,
        }

    def get_server(self) -> FoxgloveServer:
        """Get or initialize the underlying FoxgloveServer instance."""
        if self.server is None:
            self.server = FoxgloveServer(
                host=self.host,
                port=self.port,
                name="dora-openarm-foxglove-server",
            )
        return self.server

    async def setup_channels(self) -> None:
        """Register Foxglove channels for Robot Description, JointState, TF, and Quest Inputs."""
        server = self.get_server()

        self._robot_desc_channel_id = await server.add_channel(
            ChannelWithoutId(
                topic="/robot_description",
                encoding="json",
                schemaName="std_msgs/msg/String",
                schema=ROBOT_DESCRIPTION_SCHEMA,
                schemaEncoding="jsonschema",
            )
        )

        self._joint_channel_id = await server.add_channel(
            ChannelWithoutId(
                topic="/robot/joint_states",
                encoding="json",
                schemaName="foxglove.JointState",
                schema=JOINT_STATE_SCHEMA,
                schemaEncoding="jsonschema",
            )
        )

        self._tf_channel_id = await server.add_channel(
            ChannelWithoutId(
                topic="/tf",
                encoding="json",
                schemaName="foxglove.FrameTransforms",
                schema=FRAME_TRANSFORMS_SCHEMA,
                schemaEncoding="jsonschema",
            )
        )

        self._quest_channel_id = await server.add_channel(
            ChannelWithoutId(
                topic="/quest/inputs",
                encoding="json",
                schemaName="custom.QuestInputs",
                schema=QUEST_INPUTS_SCHEMA,
                schemaEncoding="jsonschema",
            )
        )

        logger.info(
            f"Foxglove channels registered: /robot_description ({self._robot_desc_channel_id}), "
            f"/robot/joint_states ({self._joint_channel_id}), /tf ({self._tf_channel_id}), "
            f"/quest/inputs ({self._quest_channel_id})"
        )

        # Publish initial URDF robot description if available
        if self.urdf_path and self.urdf_path.exists():
            self.publish_urdf_description(self.urdf_path)

    def publish_urdf_description(self, urdf_path: pathlib.Path) -> None:
        """Read and publish URDF with mesh URLs rewritten to local asset HTTP server."""
        try:
            with open(urdf_path, "r", encoding="utf-8") as f:
                urdf_text = f.read()

            # Rewrite package:// URLs to local HTTP server so Foxglove Web/Desktop can load 3D meshes
            http_base = f"http://localhost:{self.mesh_http_port}/"
            urdf_text_rewritten = urdf_text.replace("package://nana_v3_description/", http_base)

            if self._robot_desc_channel_id is not None:
                msg = {"data": urdf_text_rewritten}
                self.send_raw_message(self._robot_desc_channel_id, time.time_ns(), msg)
                logger.info(f"Published URDF robot description from {urdf_path} (meshes mapped to {http_base})")
        except Exception as e:
            logger.error(f"Failed to publish URDF robot description: {e}")

    def send_raw_message(self, channel_id: int, timestamp_ns: int, data: dict[str, Any]) -> None:
        """Thread-safe dispatch of serialized JSON payload to Foxglove WebSocket."""
        if self.loop is None or not self.loop.is_running():
            return
        payload = json.dumps(data).encode("utf-8")
        asyncio.run_coroutine_threadsafe(
            self.server.send_message(channel_id, timestamp_ns, payload),
            self.loop,
        )

    def update_joint_positions(
        self,
        side: str,
        qpos_raw: list[float] | tuple[float, ...],
        timestamp_ns: int | None = None,
    ) -> None:
        """Update joint positions for left or right arm and broadcast /robot/joint_states."""
        if timestamp_ns is None:
            timestamp_ns = time.time_ns()

        # qpos_raw: [j1, j2, j3, j4, j5, j6, j7, gripper]
        qpos_list = [float(v) for v in qpos_raw]
        if len(qpos_list) >= 8:
            joints = qpos_list[:7]
            gripper = qpos_list[7]
            # Map gripper to dual finger joints
            finger1 = -abs(gripper)
            finger2 = abs(gripper)
            full_arm = joints + [finger1, finger2]
        elif len(qpos_list) == 7:
            full_arm = qpos_list + [0.0, 0.0]
        else:
            full_arm = (qpos_list + [0.0] * 9)[:9]

        if side == "left":
            self._left_qpos = full_arm
        elif side == "right":
            self._right_qpos = full_arm

        if self._joint_channel_id is not None:
            # Map both openarm_* and nana_v3_* joint names for full URDF compatibility
            all_positions = (
                self._left_qpos
                + self._right_qpos
                + self._left_qpos[:7]
                + self._right_qpos[:7]
            )
            msg = {
                "timestamp": _ns_to_timestamp_obj(timestamp_ns),
                "name": ALL_JOINT_NAMES,
                "position": all_positions,
                "velocity": [],
                "effort": [],
            }
            self.send_raw_message(self._joint_channel_id, timestamp_ns, msg)

    def update_transform(
        self,
        child_frame_id: str,
        pose: list[float] | tuple[float, ...],
        parent_frame_id: str = "arm_origin",
        timestamp_ns: int | None = None,
    ) -> None:
        """Update a 3D pose transform and broadcast /tf."""
        if timestamp_ns is None:
            timestamp_ns = time.time_ns()

        # pose: [x, y, z, qw, qx, qy, qz, ...] (scalar-first quaternion [qw, qx, qy, qz])
        if len(pose) < 7:
            return

        x, y, z = float(pose[0]), float(pose[1]), float(pose[2])
        qw, qx, qy, qz = float(pose[3]), float(pose[4]), float(pose[5]), float(pose[6])

        self._transforms[child_frame_id] = {
            "timestamp": _ns_to_timestamp_obj(timestamp_ns),
            "parent_frame_id": parent_frame_id,
            "child_frame_id": child_frame_id,
            "translation": {"x": x, "y": y, "z": z},
            "rotation": {"x": qx, "y": qy, "z": qz, "w": qw},
        }

        if self._tf_channel_id is not None:
            msg = {
                "transforms": list(self._transforms.values()),
            }
            self.send_raw_message(self._tf_channel_id, timestamp_ns, msg)

    def update_quest_input(self, key: str, value: Any, timestamp_ns: int | None = None) -> None:
        """Update trigger or button value and broadcast /quest/inputs."""
        if timestamp_ns is None:
            timestamp_ns = time.time_ns()

        if key in self._quest_inputs:
            self._quest_inputs[key] = value

        if self._quest_channel_id is not None:
            msg = {
                "timestamp": _ns_to_timestamp_obj(timestamp_ns),
                **self._quest_inputs,
            }
            self.send_raw_message(self._quest_channel_id, timestamp_ns, msg)
