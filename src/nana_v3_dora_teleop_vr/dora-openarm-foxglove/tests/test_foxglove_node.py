"""Tests for dora_openarm_foxglove node and server logic."""

import json
import numpy as np
import pyarrow as pa
import pytest

from dora_openarm_foxglove.main import extract_bool, extract_float, extract_values, parse_timestamp_ns
from dora_openarm_foxglove.schemas import (
    FRAME_TRANSFORMS_SCHEMA,
    JOINT_STATE_SCHEMA,
    QUEST_INPUTS_SCHEMA,
    ROBOT_DESCRIPTION_SCHEMA,
)
from dora_openarm_foxglove.server import ALL_JOINT_NAMES, FoxgloveVisualizerServer


def test_schemas_are_valid_json():
    """Verify that all schemas are valid JSON strings."""
    for s in (JOINT_STATE_SCHEMA, FRAME_TRANSFORMS_SCHEMA, QUEST_INPUTS_SCHEMA, ROBOT_DESCRIPTION_SCHEMA):
        parsed = json.loads(s)
        assert "type" in parsed
        assert parsed["type"] == "object"


def test_extract_values():
    """Test extract_values with raw numpy array and PyArrow StructArray."""
    raw = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    np.testing.assert_array_equal(extract_values(raw), raw)

    struct_type = pa.struct({"qpos": pa.list_(pa.float32())})
    pa_val = pa.array([{"qpos": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]}], type=struct_type)
    extracted = extract_values(pa_val, "qpos")
    assert len(extracted) == 8
    assert np.isclose(extracted[0], 0.1)


def test_extract_primitives():
    """Test float and boolean extractions."""
    assert extract_float(pa.array([0.75], type=pa.float32())) == pytest.approx(0.75)
    assert extract_float(0.5) == pytest.approx(0.5)

    assert extract_bool(pa.array([True], type=pa.bool_())) is True
    assert extract_bool(pa.array([False], type=pa.bool_())) is False
    assert extract_bool(True) is True


def test_server_joint_and_transform_updates():
    """Test server caching and formatting."""
    server = FoxgloveVisualizerServer()
    server.update_joint_positions("left", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
    assert len(server._left_qpos) == 9
    assert np.isclose(server._left_qpos[7], -0.8)
    assert np.isclose(server._left_qpos[8], 0.8)

    server.update_transform("quest_controller_right", [0.1, 0.2, 0.3, 1.0, 0.0, 0.0, 0.0, 0.5])
    assert "quest_controller_right" in server._transforms
    tf_data = server._transforms["quest_controller_right"]
    assert tf_data["translation"] == {"x": 0.1, "y": 0.2, "z": 0.3}
    assert tf_data["rotation"] == {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}

    server.update_quest_input("trigger_left_pct", 75.5)
    server.update_quest_input("button_a", True)
    assert server._quest_inputs["trigger_left_pct"] == 75.5
    assert server._quest_inputs["button_a"] is True


def test_all_joint_names_contains_both_openarm_and_nana():
    """Test that all joint names include both naming conventions for URDF matching."""
    assert "openarm_left_joint1" in ALL_JOINT_NAMES
    assert "openarm_right_joint1" in ALL_JOINT_NAMES
    assert "nana_v3_left_joint1" in ALL_JOINT_NAMES
    assert "nana_v3_right_joint1" in ALL_JOINT_NAMES
