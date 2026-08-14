"""Foxglove schema definitions for dora-openarm-foxglove."""

import json

# Schema for /robot/joint_states using standard foxglove.JointState schema
JOINT_STATE_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "timestamp": {
            "type": "object",
            "properties": {
                "sec": {"type": "integer"},
                "nsec": {"type": "integer"}
            },
            "required": ["sec", "nsec"]
        },
        "name": {
            "type": "array",
            "items": {"type": "string"}
        },
        "position": {
            "type": "array",
            "items": {"type": "number"}
        },
        "velocity": {
            "type": "array",
            "items": {"type": "number"}
        },
        "effort": {
            "type": "array",
            "items": {"type": "number"}
        }
    },
    "required": ["timestamp", "name", "position"]
})

# Schema for /tf using standard foxglove.FrameTransforms schema
FRAME_TRANSFORMS_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "transforms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {
                        "type": "object",
                        "properties": {
                            "sec": {"type": "integer"},
                            "nsec": {"type": "integer"}
                        },
                        "required": ["sec", "nsec"]
                    },
                    "parent_frame_id": {"type": "string"},
                    "child_frame_id": {"type": "string"},
                    "translation": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "z": {"type": "number"}
                        },
                        "required": ["x", "y", "z"]
                    },
                    "rotation": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "z": {"type": "number"},
                            "w": {"type": "number"}
                        },
                        "required": ["x", "y", "z", "w"]
                    }
                },
                "required": ["timestamp", "parent_frame_id", "child_frame_id", "translation", "rotation"]
            }
        }
    },
    "required": ["transforms"]
})

# Schema for /quest/inputs custom telemetry schema
QUEST_INPUTS_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "timestamp": {
            "type": "object",
            "properties": {
                "sec": {"type": "integer"},
                "nsec": {"type": "integer"}
            },
            "required": ["sec", "nsec"]
        },
        "trigger_left_pct": {"type": "number"},
        "trigger_right_pct": {"type": "number"},
        "button_a": {"type": "boolean"},
        "button_b": {"type": "boolean"},
        "button_x": {"type": "boolean"},
        "button_y": {"type": "boolean"}
    },
    "required": ["timestamp", "trigger_left_pct", "trigger_right_pct", "button_a", "button_b", "button_x", "button_y"]
})

# Schema for /robot_description (std_msgs/String)
ROBOT_DESCRIPTION_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "data": {"type": "string"}
    },
    "required": ["data"]
})
