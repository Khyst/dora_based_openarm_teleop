# Copyright 2026 Enactic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""dora-rs node providing a Three.js 3D Web UI for OpenArm teleoperation and trajectory dataset recording."""

import argparse
import asyncio
import collections
from contextlib import asynccontextmanager
import dataclasses
import datetime
from collections.abc import AsyncIterable
import json
import os
import pathlib
import time
import dora
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.templating import Jinja2Templates
import pyarrow as pa
import uvicorn
import yaml

base_dir = os.path.dirname(__file__)
templates = Jinja2Templates(directory=f"{base_dir}/templates")

node = None
auto_open = False
port = 8000
tasks = []
record_type = "waypoint"
vr_data_dir: pathlib.Path | None = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Open Web browser automatically if requested."""
    if auto_open:
        url = f"http://127.0.0.1:{port}"
        await asyncio.create_subprocess_exec("open", url)
    yield

app = FastAPI(lifespan=_lifespan)

# Mount nana_v3_description static files for Three.js 3D Mesh / URDF Loader
curr_file = pathlib.Path(__file__).resolve()
nana_desc_dir = None
for p in [curr_file] + list(curr_file.parents):
    if (p / "nana_v3_description").exists():
        nana_desc_dir = p / "nana_v3_description"
        break
    elif (p / "src" / "nana_v3_description").exists():
        nana_desc_dir = p / "src" / "nana_v3_description"
        break

if nana_desc_dir and nana_desc_dir.exists():
    app.mount("/nana_v3_description", StaticFiles(directory=str(nana_desc_dir)), name="nana_v3_description")
    if (nana_desc_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(nana_desc_dir / "assets")), name="assets")

# Locate nana_v3_individual directory for dataset recording (vr_data)
nana_individual_dir = None
for p in [curr_file] + list(curr_file.parents):
    if (p / "src" / "nana_v3_individual").exists():
        nana_individual_dir = (p / "src" / "nana_v3_individual").resolve()
        break
    elif (p / "nana_v3_individual").exists():
        nana_individual_dir = (p / "nana_v3_individual").resolve()
        break

if nana_individual_dir is None:
    for p in list(curr_file.parents):
        if (p / "src").exists():
            nana_individual_dir = (p / "src" / "nana_v3_individual").resolve()
            break


@dataclasses.dataclass
class State:
    """Current system & UI state."""

    collecting: bool = False
    running: bool = True
    episode_number: int = 1
    task_index: int = 0
    task_title: str = "OpenArm Teleop Task"
    arm_status_right: str = "stopped"
    arm_status_left: str = "stopped"
    trigger_pressed_right: bool = False
    trigger_pressed_left: bool = False
    waypoints_count: int = 0
    record_type: str = "waypoint"
    joint_states: dict = dataclasses.field(
        default_factory=lambda: {
            "left": [0.0] * 7,
            "right": [0.0] * 7,
        }
    )
    tracked_poses: dict = dataclasses.field(
        default_factory=lambda: {
            "hmd": {"x": 0.0, "y": 1.5, "z": 0.0, "qx": 0.0, "qy": 0.0, "qz": 0.0, "qw": 1.0},
            "controller_r": {"x": 0.2, "y": 1.0, "z": 0.3, "qx": 0.0, "qy": 0.0, "qz": 0.0, "qw": 1.0},
            "controller_l": {"x": -0.2, "y": 1.0, "z": 0.3, "qx": 0.0, "qy": 0.0, "qz": 0.0, "qw": 1.0},
        }
    )
    button_states: dict = dataclasses.field(
        default_factory=lambda: {"a": False, "b": False, "x": False, "y": False}
    )
    trigger_states: dict = dataclasses.field(
        default_factory=lambda: {"trigger_r": 0.0, "grip_r": 0.0, "trigger_l": 0.0, "grip_l": 0.0}
    )


state = State()
_state_changed = asyncio.Condition()
state_version = 0

CAMERA_INPUTS = (
    "camera_wrist_right",
    "camera_wrist_left",
    "camera_head_left",
    "camera_head_right",
    "camera_ceiling",
)

CAMERA_TIMESTAMP_WINDOW = 60
CAMERA_STALE_AFTER_S = 1.0

ARM_STATUS_INPUTS = ("arm_status_right", "arm_status_left")
VR_TRIGGER_INPUTS = ("trigger_right", "trigger_left", "grip_right", "grip_left")
VR_RECEIVE_TIMES_INPUTS = ("vr_receive_times", "vr_recv_ts")

VR_TIMESTAMP_WINDOW = 120
VR_STALE_AFTER_S = 1.0

@dataclasses.dataclass
class CameraStats:
    fps: float = 0.0
    jitter_ms: float = 0.0


camera_stats: dict[str, CameraStats] = {name: CameraStats() for name in CAMERA_INPUTS}
camera_timestamps: dict[str, collections.deque] = {
    name: collections.deque(maxlen=CAMERA_TIMESTAMP_WINDOW) for name in CAMERA_INPUTS
}


@dataclasses.dataclass
class VrStreamStats:
    fps: float = 0.0
    jitter_ms: float = 0.0


vr_stats = VrStreamStats()
vr_timestamps: collections.deque = collections.deque(maxlen=VR_TIMESTAMP_WINDOW)


def _event_ts_to_seconds(ts) -> float:
    if isinstance(ts, datetime.datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        return ts.timestamp()
    if isinstance(ts, (int, float)):
        return float(ts) / 1e9
    return time.time()


def _update_camera_stats(event_id: str, ts_s: float) -> None:
    series = camera_timestamps[event_id]
    if series and ts_s - series[-1] > CAMERA_STALE_AFTER_S:
        series.clear()
    series.append(ts_s)
    if len(series) < 2:
        return
    span = series[-1] - series[0]
    if span <= 0:
        return
    fps = (len(series) - 1) / span
    diffs = [series[i] - series[i - 1] for i in range(1, len(series))]
    jitter_ms = (max(diffs) - min(diffs)) * 1e3
    stats = camera_stats[event_id]
    stats.fps = fps
    stats.jitter_ms = jitter_ms


def _update_vr_stats(ts_s: float) -> None:
    series = vr_timestamps
    if series and ts_s - series[-1] > VR_STALE_AFTER_S:
        series.clear()
    series.append(ts_s)
    if len(series) < 2:
        return
    span = series[-1] - series[0]
    if span <= 0:
        return
    vr_stats.fps = (len(series) - 1) / span
    diffs = [series[i] - series[i - 1] for i in range(1, len(series))]
    vr_stats.jitter_ms = (max(diffs) - min(diffs)) * 1e3


async def _notify_state_changed() -> None:
    global state_version
    async with _state_changed: # Why? thread-safe
        state_version += 1
        _state_changed.notify_all()


def next_task():
    if not tasks:
        return
    state.task_index = (state.task_index + 1) % len(tasks)
    state.task_title = tasks[state.task_index].get("prompt", "OpenArm Teleop Task")


recorded_trajectory: list[dict] = []
recorded_waypoints: list[dict] = []
recording_start_time: float = 0.0


def _get_current_teleop_snapshot() -> dict:
    """Capture a snapshot of the current robot and VR teleoperation states without triggers/buttons."""
    return {
        "timestamp": time.time(),
        "joint_states": {
            "left": list(state.joint_states.get("left", [0.0] * 7)),
            "right": list(state.joint_states.get("right", [0.0] * 7)),
        },
        "tracked_poses": {
            "hmd": dict(state.tracked_poses.get("hmd", {})),
            "controller_r": dict(state.tracked_poses.get("controller_r", {})),
            "controller_l": dict(state.tracked_poses.get("controller_l", {})),
        },
    }


def _command_start():
    global recording_start_time
    if node:
        node.send_output(
            "command",
            pa.array(["start"]),
            {
                "episode_number": state.episode_number,
                "task_index": state.task_index,
            },
        )
    state.collecting = True
    state.waypoints_count = 0
    recorded_trajectory.clear()
    recorded_waypoints.clear()
    recording_start_time = time.time()
    # Save initial state snapshot
    recorded_trajectory.append(_get_current_teleop_snapshot())
    print(f"[dora-openarm-web-ui] 🔴 Started recording episode {state.episode_number}")


def _command_success(dataset_data=None):
    global recording_start_time
    if node:
        node.send_output("command", pa.array(["success"]))
    state.collecting = False
    
    end_time = time.time()
    start_time = recording_start_time if recording_start_time > 0 else end_time

    # Construct clean dataset payload according to record_type
    base_data = {
        "episode_number": state.episode_number,
        "task_index": state.task_index,
        "task_title": state.task_title,
        "record_type": record_type,
        "start_time": start_time,
        "end_time": end_time,
        "duration_s": round(end_time - start_time, 3),
    }

    if record_type == "waypoint":
        # Extract waypoints only
        wp_list = list(recorded_waypoints)
        if dataset_data and isinstance(dataset_data, dict):
            if dataset_data.get("waypoints"):
                wp_list = dataset_data["waypoints"]
            elif dataset_data.get("trajectories") and not recorded_waypoints:
                wp_list = dataset_data["trajectories"]
        
        base_data["waypoints_count"] = len(wp_list)
        base_data["waypoints"] = wp_list
        final_dataset = base_data
    else:
        # Extract trajectories only
        traj_list = list(recorded_trajectory)
        if dataset_data and isinstance(dataset_data, dict) and dataset_data.get("trajectories"):
            traj_list = dataset_data["trajectories"]
        
        base_data["samples_count"] = len(traj_list)
        base_data["trajectories"] = traj_list
        final_dataset = base_data

    # Save dataset file
    try:
        if vr_data_dir:
            out_dir = vr_data_dir
        elif os.getenv("VR_DATA_DIR"):
            out_dir = pathlib.Path(os.getenv("VR_DATA_DIR")).resolve()
        elif nana_individual_dir:
            out_dir = (nana_individual_dir / "vr_data").resolve()
        else:
            out_dir = pathlib.Path("vr_data").resolve()

        out_dir.mkdir(parents=True, exist_ok=True)
        filepath = out_dir / f"episode_{state.episode_number}_{int(time.time())}.json"
        
        def _clean_item(item):
            if isinstance(item, dict):
                return {
                    k: _clean_item(v)
                    for k, v in item.items()
                    if k not in ("triggers", "buttons", "trigger_states", "button_states")
                }
            elif isinstance(item, list):
                return [_clean_item(v) for v in item]
            return item

        final_dataset = _clean_item(final_dataset)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(final_dataset, f, indent=2)

        data_count = len(final_dataset.get("waypoints" if record_type == "waypoint" else "trajectories", []))
        print(
            f"[dora-openarm-web-ui] ✅ Saved episode {state.episode_number} dataset to: {filepath} "
            f"(mode: {record_type}, count: {data_count})"
        )
    except Exception as e:
        print(f"[dora-openarm-web-ui] ❌ Error saving dataset to {out_dir}: {e}")

    state.episode_number += 1
    next_task()


def _command_fail():
    if node:
        node.send_output("command", pa.array(["fail"]))
    state.collecting = False
    state.episode_number += 1
    next_task()


def _command_quit():
    if node:
        node.send_output("command", pa.array(["quit"]))
    state.running = False


def _command_arm_start():
    if node:
        node.send_output("arm_command", pa.array(["start"]))


def _command_arm_stop():
    if node:
        node.send_output("arm_command", pa.array(["stop"]))


@app.get("/", response_class=HTMLResponse)
def _root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="root.html",
        context={"state": state, "state_version": state_version},
    )


@app.post("/start")
async def _start(request: Request):
    _command_start()
    await _notify_state_changed()
    if request.headers.get("accept") == "application/json":
        return JSONResponse({"status": "started", "collecting": state.collecting})
    return RedirectResponse(request.url_for("_root"), 303)


@app.post("/success")
async def _success(request: Request):
    dataset_data = None
    if request.headers.get("content-type") == "application/json":
        try:
            dataset_data = await request.json()
        except Exception:
            pass
    _command_success(dataset_data)
    await _notify_state_changed()
    if request.headers.get("accept") == "application/json" or request.headers.get("content-type") == "application/json":
        return JSONResponse({"status": "success", "episode_number": state.episode_number})
    return RedirectResponse(request.url_for("_root"), 303)


@app.post("/waypoint")
async def _waypoint(request: Request):
    if state.collecting:
        state.waypoints_count += 1
        recorded_waypoints.append(_get_current_teleop_snapshot())
        await _notify_state_changed()
    return JSONResponse({"waypoints_count": state.waypoints_count})


@app.post("/skip")
async def _skip(request: Request):
    next_task()
    await _notify_state_changed()
    return RedirectResponse(request.url_for("_root"), 303)


@app.post("/fail")
async def _fail(request: Request):
    _command_fail()
    await _notify_state_changed()
    return RedirectResponse(request.url_for("_root"), 303)


@app.post("/cancel")
async def _cancel(request: Request):
    if node:
        node.send_output("command", pa.array(["cancel"]))
    state.collecting = False
    state.episode_number += 1
    await _notify_state_changed()
    return RedirectResponse(request.url_for("_root"), 303)


@app.post("/quit")
def _quit(request: Request):
    _command_quit()
    return RedirectResponse(request.url_for("_root"), 303)


@app.post("/arm/start")
async def _arm_start(request: Request):
    _command_arm_start()
    await _notify_state_changed()
    return RedirectResponse(request.url_for("_root"), 303)


@app.post("/arm/stop")
async def _arm_stop(request: Request):
    _command_arm_stop()
    await _notify_state_changed()
    return RedirectResponse(request.url_for("_root"), 303)


@app.get("/events", response_class=EventSourceResponse)
async def _events(request: Request) -> AsyncIterable[ServerSentEvent]:
    try:
        last_version = int(request.query_params.get("since"))
    except (TypeError, ValueError):
        last_version = state_version
    while state.running:
        async with _state_changed:
            await _state_changed.wait_for(
                lambda: state_version != last_version or not state.running
            )
        if not state.running:
            break
        last_version = state_version
        yield ServerSentEvent(
            data={
                "collecting": state.collecting,
                "episode_number": state.episode_number,
                "task_index": state.task_index,
                "task_title": state.task_title,
                "arm_status_right": state.arm_status_right,
                "arm_status_left": state.arm_status_left,
                "trigger_pressed_right": state.trigger_pressed_right,
                "trigger_pressed_left": state.trigger_pressed_left,
                "joint_states": state.joint_states,
                "tracked_poses": state.tracked_poses,
                "button_states": state.button_states,
                "trigger_states": state.trigger_states,
                "waypoints_count": state.waypoints_count,
                "record_type": state.record_type,
            },
            id=str(state_version),
        )


@app.get("/stats", response_class=EventSourceResponse)
async def _stats() -> AsyncIterable[ServerSentEvent]:
    while state.running:
        now = time.time()
        snapshot = {}
        for name, s in camera_stats.items():
            series = camera_timestamps[name]
            if not series or now - series[-1] > CAMERA_STALE_AFTER_S:
                snapshot[name] = {"fps": 0.0, "jitter_ms": 0.0}
            else:
                snapshot[name] = {"fps": s.fps, "jitter_ms": s.jitter_ms}
        yield ServerSentEvent(data=snapshot)
        await asyncio.sleep(0.5)


@app.get("/vr-stats", response_class=EventSourceResponse)
async def _vr_stats() -> AsyncIterable[ServerSentEvent]:
    while state.running:
        now = time.time()
        if not vr_timestamps or now - vr_timestamps[-1] > VR_STALE_AFTER_S:
            snapshot = {"fps": 0.0, "jitter_ms": 0.0}
        else:
            snapshot = {"fps": vr_stats.fps, "jitter_ms": vr_stats.jitter_ms}
        yield ServerSentEvent(data=snapshot)
        await asyncio.sleep(0.5)


def load_yaml(path):
    if path is None or not pathlib.Path(path).exists():
        return {
            "location": "Lab",
            "operator": "User",
            "tasks": [
                {
                    "prompt": "OpenArm Teleop Task",
                    "description": "Teleoperation data collection episode",
                }
            ],
        }
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _parse_pose(val):
    """Helper to convert pyarrow/dict pose into standard dict {x, y, z, qx, qy, qz, qw}."""
    if val is None:
        return None
    try:
        arr = None

        # Case 1: PyArrow object via to_pylist()
        if hasattr(val, "to_pylist"):
            plist = val.to_pylist()
            if plist and isinstance(plist, list):
                item = plist[0]
                if isinstance(item, dict) and "pose" in item:
                    arr = item["pose"]
                elif isinstance(item, (list, tuple)):
                    arr = item
                elif isinstance(item, (int, float)) and len(plist) >= 7:
                    arr = plist

        # Case 2: PyArrow object via as_py()
        if arr is None and hasattr(val, "as_py"):
            py_val = val.as_py()
            if isinstance(py_val, list) and py_val:
                item = py_val[0]
                if isinstance(item, dict) and "pose" in item:
                    arr = item["pose"]
                elif isinstance(item, (list, tuple)):
                    arr = item
            elif isinstance(py_val, dict) and "pose" in py_val:
                arr = py_val["pose"]
            elif isinstance(py_val, (list, tuple)):
                arr = py_val

        # Case 3: Standard Python Dict
        if arr is None and isinstance(val, dict):
            if "pose" in val:
                arr = val["pose"]
            elif "x" in val:
                return {
                    "x": float(val.get("x", 0.0)),
                    "y": float(val.get("y", 0.0)),
                    "z": float(val.get("z", 0.0)),
                    "qx": float(val.get("qx", 0.0)),
                    "qy": float(val.get("qy", 0.0)),
                    "qz": float(val.get("qz", 0.0)),
                    "qw": float(val.get("qw", 1.0)),
                }

        # Case 4: Standard Python List or Tuple
        if arr is None and isinstance(val, (list, tuple)):
            if val and isinstance(val[0], dict) and "pose" in val[0]:
                arr = val[0]["pose"]
            else:
                arr = val

        if arr is not None and len(arr) >= 7:
            px, py, pz = float(arr[0]), float(arr[1]), float(arr[2])
            qw, qx, qy, qz = float(arr[3]), float(arr[4]), float(arr[5]), float(arr[6])

            return {
                "x": px,
                "y": py,
                "z": pz,
                "qx": qx,
                "qy": qy,
                "qz": qz,
                "qw": qw,
            }
    except Exception as e:
        print(f"[dora-openarm-web-ui] Exception in _parse_pose: {e}")
    return None


def _parse_float_array(val):
    """Safely extract float array from pyarrow StructArray, ListArray, dict, or list/tuple."""
    if val is None:
        return []
    try:
        # Case 1: PyArrow StructArray or ListArray via to_pylist()
        if hasattr(val, "to_pylist"):
            pylist = val.to_pylist()
            if not pylist:
                return []
            item = pylist[0]
            if isinstance(item, dict):
                # Look for qpos, position, new_position, or values key
                for k in ("qpos", "new_position", "position", "values", "joint_states"):
                    if k in item and isinstance(item[k], (list, tuple)):
                        return [float(x) for x in item[k]]
                # Fallback: check values of dictionary if numeric
                dict_vals = list(item.values())
                if dict_vals and isinstance(dict_vals[0], (int, float)):
                    return [float(x) for x in dict_vals]
                if dict_vals and isinstance(dict_vals[0], (list, tuple)):
                    return [float(x) for x in dict_vals[0]]
            elif isinstance(item, (int, float)):
                return [float(x) for x in pylist]
            elif isinstance(item, (list, tuple)):
                return [float(x) for x in item]

        # Case 2: PyArrow Struct/Scalar via as_py()
        if hasattr(val, "as_py"):
            py_val = val.as_py()
            if isinstance(py_val, dict):
                for k in ("qpos", "new_position", "position", "values", "joint_states"):
                    if k in py_val and isinstance(py_val[k], (list, tuple)):
                        return [float(x) for x in py_val[k]]
            elif isinstance(py_val, (list, tuple)):
                if py_val and isinstance(py_val[0], dict):
                    item = py_val[0]
                    for k in ("qpos", "new_position", "position", "values", "joint_states"):
                        if k in item and isinstance(item[k], (list, tuple)):
                            return [float(x) for x in item[k]]
                return [float(x) for x in py_val]

        # Case 3: Standard Python Dict
        if isinstance(val, dict):
            for k in ("qpos", "new_position", "position", "values", "joint_states"):
                if k in val and isinstance(val[k], (list, tuple)):
                    return [float(x) for x in val[k]]

        # Case 4: Standard Python List or Tuple
        if isinstance(val, (list, tuple)):
            if val and isinstance(val[0], dict):
                item = val[0]
                for k in ("qpos", "new_position", "position", "values", "joint_states"):
                    if k in item and isinstance(item[k], (list, tuple)):
                        return [float(x) for x in item[k]]
            return [float(x) for x in val]
    except Exception as e:
        print(f"[dora-openarm-web-ui] Exception in _parse_float_array: {e}")
    return []


def _parse_float_scalar(val, default: float = 0.0) -> float:
    """Safely extract float scalar from any pyarrow object or primitive."""
    if val is None:
        return default
    try:
        if hasattr(val, "to_pylist"):
            plist = val.to_pylist()
            if plist:
                return float(plist[0])
        if hasattr(val, "as_py"):
            py_v = val.as_py()
            if isinstance(py_v, (list, tuple)) and py_v:
                return float(py_v[0])
            return float(py_v)
        if isinstance(val, (list, tuple)) and val:
            return float(val[0])
        return float(val)
    except Exception:
        return default


def _parse_bool_scalar(val, default: bool = False) -> bool:
    """Safely extract boolean scalar from any pyarrow object or primitive."""
    if val is None:
        return default
    try:
        if hasattr(val, "to_pylist"):
            plist = val.to_pylist()
            if plist:
                return bool(plist[0])
        if hasattr(val, "as_py"):
            py_v = val.as_py()
            if isinstance(py_v, (list, tuple)) and py_v:
                return bool(py_v[0])
            return bool(py_v)
        if isinstance(val, (list, tuple)) and val:
            return bool(val[0])
        return bool(val)
    except Exception:
        return default


@app.post("/button")
async def _button(request: Request):
    try:
        data = await request.json()
        btn = str(data.get("button", "")).lower()
        pressed = bool(data.get("pressed", False))
        if btn in ("a", "b", "x", "y"):
            state.button_states[btn] = pressed
            if pressed:
                if btn in ("a", "x"):
                    if state.collecting:
                        _command_success()
                    else:
                        _command_start()
                elif btn in ("b", "y"):
                    if state.collecting:
                        state.waypoints_count += 1
                        recorded_waypoints.append(_get_current_teleop_snapshot())
            await _notify_state_changed()
    except Exception as e:
        print(f"[dora-openarm-web-ui] Error in /button: {e}")
    return JSONResponse({
        "status": "ok",
        "button_states": state.button_states,
        "collecting": state.collecting,
        "waypoints_count": state.waypoints_count
    })


async def _main_uvicorn(server):
    await server.serve()


async def _main_dora(server):

    _command_arm_start()

    last_values = {}

    while state.running:
        
        if node.is_empty(): # Why?: If there is no event, it will wait for 0.001 seconds and continue.
            await asyncio.sleep(0.001)
            continue
        
        event = node.next()
        
        if event["type"] == "STOP":
            state.running = False
        
        elif event["type"] == "INPUT":

            event_id = event["id"]

            val = event["value"]

            try:
                if event_id == "tick":
                    
                    if state.collecting: # 상태 관리
                        recorded_trajectory.append(_get_current_teleop_snapshot())

                    continue

                if event_id in CAMERA_INPUTS:
                    _update_camera_stats(
                        event_id,
                        _event_ts_to_seconds(event["metadata"].get("timestamp")),
                    )

                    continue

                if event_id in ARM_STATUS_INPUTS:
                    str_val = str(val[0].as_py()) if hasattr(val, "__getitem__") else str(val)
                    if getattr(state, event_id) != str_val:
                        setattr(state, event_id, str_val)
                        await _notify_state_changed()

                    continue

                if event_id in VR_RECEIVE_TIMES_INPUTS:
                    if hasattr(val, "to_pylist"):
                        for ts_ns in val.to_pylist():
                            _update_vr_stats(float(ts_ns) / 1e9)

                    continue

                if event_id in VR_TRIGGER_INPUTS:
                    flt_val = _parse_float_scalar(val, 0.0)

                    if event_id == "trigger_right":
                        state.trigger_states["trigger_r"] = flt_val
                        state.trigger_pressed_right = bool(flt_val > 0.5)

                    elif event_id == "grip_right":
                        state.trigger_states["grip_r"] = flt_val

                    elif event_id == "trigger_left":
                        state.trigger_states["trigger_l"] = flt_val
                        state.trigger_pressed_left = bool(flt_val > 0.5)

                    elif event_id == "grip_left":
                        state.trigger_states["grip_l"] = flt_val

                    await _notify_state_changed()

                    continue

                if event_id in ("pose_right", "pose_left", "pose_reference", "pose_hmd"):
                    parsed = _parse_pose(val)

                    if parsed:
                        key = "controller_r" if event_id == "pose_right" else ("controller_l" if event_id == "pose_left" else "hmd")
                        state.tracked_poses[key] = parsed
                        await _notify_state_changed()

                    continue

                if event_id in ("position_left", "position_right"):
                    arr = _parse_float_array(val)

                    if arr:
                        side = "left" if "left" in event_id else "right"
                        state.joint_states[side] = arr
                        await _notify_state_changed()

                    continue

                if event_id in ("button_a", "button_b", "button_x", "button_y"):
                    btn_val = _parse_bool_scalar(val, False)

                    btn_name = event_id.replace("button_", "")
                    state.button_states[btn_name] = btn_val

                    triggered = btn_val and not last_values.get(event_id, False)
                    last_values[event_id] = btn_val

                    if triggered:
                        # Recording Mode Toggle on Button X or Button A
                        if event_id in ("button_a", "button_x"):
                            if state.collecting:
                                _command_success()
                            else:
                                _command_start()
                        # Waypoint Trajectory Capture on Button Y or Button B
                        elif event_id in ("button_b", "button_y"):
                            if state.collecting:
                                state.waypoints_count += 1
                                recorded_waypoints.append(_get_current_teleop_snapshot())

                    await _notify_state_changed()

                    continue

            except Exception as e:
                print(f"[dora-openarm-web-ui] Error processing event {event_id}: {e}")

    server.should_exit = True


async def _main_async():

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")

    server = uvicorn.Server(config)

    task_uvicorn = asyncio.create_task(_main_uvicorn(server))

    task_dora = asyncio.create_task(_main_dora(server))

    await task_uvicorn

    state.running = False

    await task_dora


def main():

    global node, tasks, auto_open, port, vr_data_dir, record_type

    parser = argparse.ArgumentParser(description="Three.js 3D Web UI & Trajectory Recording for OpenArm")

    parser.add_argument(
        "--metadata-file",
        default=os.getenv("METADATA_FILE"),
        help="Metadata file path",
        type=pathlib.Path,
    )

    parser.add_argument(
        "--auto-open",
        action=argparse.BooleanOptionalAction,
        default=os.getenv("AUTO_OPEN", "") == "yes",
        help="Open browser automatically",
    )

    default_port = 8000

    parser.add_argument(
        "--port",
        default=int(os.getenv("PORT", default_port)),
        help=f"Web server port (default {default_port})",
        type=int,
    )

    parser.add_argument(
        "--vr-data-dir",
        default=os.getenv("VR_DATA_DIR"),
        help="Directory path to save vr_data recorded episodes (default: nana_v3_individual/vr_data)",
        type=pathlib.Path,
    )

    parser.add_argument(
        "--record-type",
        choices=["trajectory", "trajectories", "waypoint", "waypoints"],
        default=os.getenv("RECORD_TYPE", "waypoint"),
        help="Record data type to include in JSON dataset: 'waypoint' (default) or 'trajectory'",
        type=str,
    )

    args = parser.parse_args()

    auto_open = args.auto_open

    port = args.port

    if args.vr_data_dir:
        vr_data_dir = args.vr_data_dir.resolve()

    raw_type = str(args.record_type or "waypoint").strip().lower()

    if "trajectory" in raw_type or "trajectories" in raw_type:
        record_type = "trajectory"
    else:
        record_type = "waypoint"
        
    state.record_type = record_type

    print(f"[dora-openarm-web-ui] Dataset Recording Type: {record_type.upper()}")

    metadata = load_yaml(args.metadata_file)

    tasks = metadata.get("tasks", [{"prompt": "OpenArm Teleop Task"}])

    state.task_title = tasks[state.task_index].get("prompt", "OpenArm Teleop Task")

    try:
        node = dora.Node()

    except Exception as e:

        print(f"[dora-openarm-web-ui] Running without Dora environment ({e})")

    asyncio.run(_main_async())


if __name__ == "__main__":
    
    main()
